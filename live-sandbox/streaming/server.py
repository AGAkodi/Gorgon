"""
WebSocket streaming server for the Interactive Live Sandbox (Layer 2).

Bridges the gap between a Playwright-controlled headless Chromium instance
and the user's browser: streams live screencast frames out to the frontend
over WebSocket, and relays mouse/keyboard input events back into the
sandboxed page via CDP.

Protocol (JSON over WebSocket):

  Client → Server:
    { "type": "start", "url": "https://..." }       — start a new session
    { "type": "stop" }                                — end the session
    { "type": "mouse", "action": "click"|"move"|"down"|"up",
      "x": int, "y": int, "button": "left"|"right"|"middle" }
    { "type": "keyboard", "action": "down"|"up"|"type",
      "key": str, "text": str }
    { "type": "scroll", "x": int, "y": int,
      "deltaX": int, "deltaY": int }

  Server → Client:
    { "type": "frame", "data": "<base64-jpeg>", "timestamp": int }
    { "type": "session_started", "session_id": str }
    { "type": "session_ended" }
    { "type": "simulation_result", "data": { ... } }
    { "type": "error", "message": str }
"""

import asyncio
import base64
import json
import sys
import time
from pathlib import Path

import websockets

# Allow imports from sibling directories
sys.path.insert(0, str(Path(__file__).parent.parent / "orchestration"))
sys.path.insert(0, str(Path(__file__).parent.parent / "wallet-inject"))
sys.path.insert(0, str(Path(__file__).parent.parent / "interceptor"))

from session import Session  # noqa: E402
from injector import WalletInjector  # noqa: E402
from handler import InterceptHandler  # noqa: E402


class StreamingServer:
    """WebSocket server that streams a sandboxed browser session to the frontend."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
        self.host = host
        self.port = port
        self._session: Session | None = None
        self._cdp_session = None
        self._ws = None
        self._running = False
        self._injector: WalletInjector | None = None
        self._interceptor = InterceptHandler(on_simulation_result=self.broadcast_simulation_result)

    async def _on_wallet_intercept(self, payload: dict):
        """Callback triggered when page JS calls standard wallet methods."""
        print(f"[Streaming] Intercepted wallet call: {payload.get('method')}")
        await self._interceptor.handle(payload, self._injector)

    async def _start_screencast(self):
        """Start CDP screencast — sends frames as fast as the browser produces them."""
        if not self._session or not self._session.page:
            return

        page = self._session.page
        # Get CDP session from the page
        self._cdp_session = await page.context.new_cdp_session(page)

        # Listen for screencast frames
        self._cdp_session.on("Page.screencastFrame", self._on_screencast_frame)

        # Start screencasting — JPEG at 60% quality, max 15fps for bandwidth
        await self._cdp_session.send("Page.startScreencast", {
            "format": "jpeg",
            "quality": 60,
            "maxWidth": 1280,
            "maxHeight": 800,
            "everyNthFrame": 1,
        })

    def _on_screencast_frame(self, params):
        """Handle an incoming screencast frame from CDP."""
        if not self._ws or not self._running:
            return

        frame_data = params.get("data", "")
        session_id = params.get("sessionId", 0)

        # Acknowledge the frame so CDP keeps sending
        asyncio.ensure_future(self._ack_frame(session_id))

        # Send frame to frontend
        message = json.dumps({
            "type": "frame",
            "data": frame_data,  # Already base64-encoded by CDP
            "timestamp": int(time.time() * 1000),
        })
        asyncio.ensure_future(self._safe_send(message))

    async def _ack_frame(self, session_id):
        """Acknowledge a screencast frame so CDP continues sending."""
        if self._cdp_session:
            try:
                await self._cdp_session.send("Page.screencastFrameAck", {
                    "sessionId": session_id,
                })
            except Exception:
                pass  # Session may have been torn down

    async def _safe_send(self, message: str):
        """Send a WebSocket message, ignoring errors if connection closed."""
        if self._ws:
            try:
                await self._ws.send(message)
            except websockets.exceptions.ConnectionClosed:
                pass

    async def _dispatch_mouse(self, data: dict):
        """Dispatch a mouse event to the sandboxed page via CDP."""
        if not self._cdp_session:
            return

        action = data.get("action", "click")
        x = data.get("x", 0)
        y = data.get("y", 0)
        button = data.get("button", "left")

        cdp_type_map = {
            "move": "mouseMoved",
            "down": "mousePressed",
            "up": "mouseReleased",
            "click": None,  # Handled as down + up
        }

        if action == "click":
            await self._cdp_session.send("Input.dispatchMouseEvent", {
                "type": "mousePressed",
                "x": x, "y": y,
                "button": button,
                "clickCount": 1,
            })
            await self._cdp_session.send("Input.dispatchMouseEvent", {
                "type": "mouseReleased",
                "x": x, "y": y,
                "button": button,
                "clickCount": 1,
            })
        elif action in cdp_type_map and cdp_type_map[action]:
            params = {"type": cdp_type_map[action], "x": x, "y": y, "button": button}
            if action == "down":
                params["clickCount"] = 1
            await self._cdp_session.send("Input.dispatchMouseEvent", params)

    async def _dispatch_keyboard(self, data: dict):
        """Dispatch a keyboard event to the sandboxed page via CDP."""
        if not self._cdp_session:
            return

        action = data.get("action", "type")
        key = data.get("key", "")
        text = data.get("text", "")

        if action == "type" and text:
            # Insert text directly
            await self._cdp_session.send("Input.insertText", {"text": text})
        elif action == "down":
            await self._cdp_session.send("Input.dispatchKeyEvent", {
                "type": "keyDown",
                "key": key,
            })
        elif action == "up":
            await self._cdp_session.send("Input.dispatchKeyEvent", {
                "type": "keyUp",
                "key": key,
            })

    async def _dispatch_scroll(self, data: dict):
        """Dispatch a scroll event to the sandboxed page via CDP."""
        if not self._cdp_session:
            return

        await self._cdp_session.send("Input.dispatchMouseEvent", {
            "type": "mouseWheel",
            "x": data.get("x", 640),
            "y": data.get("y", 400),
            "deltaX": data.get("deltaX", 0),
            "deltaY": data.get("deltaY", 0),
        })

    async def _handle_connection(self, ws):
        """Handle a single WebSocket client connection."""
        self._ws = ws
        self._running = True
        print(f"[Streaming] Client connected from {ws.remote_address}")

        try:
            async for raw_message in ws:
                try:
                    msg = json.loads(raw_message)
                except json.JSONDecodeError:
                    await self._safe_send(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON",
                    }))
                    continue

                msg_type = msg.get("type")

                if msg_type == "start":
                    url = msg.get("url", "")
                    if not url:
                        await self._safe_send(json.dumps({
                            "type": "error",
                            "message": "Missing 'url' field",
                        }))
                        continue

                    # Tear down any existing session
                    if self._session:
                        await self._stop_session()

                    # Start a new session
                    self._session = Session()
                    try:
                        await self._session.start(url)
                        
                        # Injected mock wallet providers
                        self._injector = WalletInjector(on_intercept=self._on_wallet_intercept)
                        await self._injector.inject(self._session.page)
                        
                        await self._start_screencast()
                        await self._safe_send(json.dumps({
                            "type": "session_started",
                            "session_id": self._session.session_id,
                        }))
                        print(f"[Streaming] Session {self._session.session_id} started for {url}")
                    except Exception as e:
                        await self._safe_send(json.dumps({
                            "type": "error",
                            "message": f"Failed to start session: {e}",
                        }))
                        if self._session:
                            await self._session.stop()
                            self._session = None

                elif msg_type == "stop":
                    await self._stop_session()
                    await self._safe_send(json.dumps({"type": "session_ended"}))

                elif msg_type == "mouse":
                    await self._dispatch_mouse(msg)

                elif msg_type == "keyboard":
                    await self._dispatch_keyboard(msg)

                elif msg_type == "scroll":
                    await self._dispatch_scroll(msg)

        except websockets.exceptions.ConnectionClosed:
            print("[Streaming] Client disconnected")
        finally:
            if self._session:
                await self._stop_session()
            self._ws = None
            self._running = False

    async def _stop_session(self):
        """Stop the current session and clean up CDP resources."""
        if self._cdp_session:
            try:
                await self._cdp_session.send("Page.stopScreencast")
            except Exception:
                pass
            try:
                await self._cdp_session.detach()
            except Exception:
                pass
            self._cdp_session = None

        if self._session:
            await self._session.stop()
            self._session = None
            print("[Streaming] Session stopped")

    async def broadcast_simulation_result(self, result: dict):
        """Broadcast a simulation result to the connected client."""
        await self._safe_send(json.dumps({
            "type": "simulation_result",
            "data": result,
        }))

    async def serve(self):
        """Start the WebSocket server."""
        print(f"[Streaming] Server starting on ws://{self.host}:{self.port}")
        async with websockets.serve(self._handle_connection, self.host, self.port):
            await asyncio.Future()  # Run forever


async def main():
    server = StreamingServer()
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
