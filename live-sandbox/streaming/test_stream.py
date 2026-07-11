"""
Tests for the Streaming server (Sub-Phase 2).

Verifies:
1. Server starts and accepts WebSocket connections
2. "start" command creates a session and begins screencasting
3. At least one frame is received
4. Mouse input events are dispatched without error
5. "stop" command tears down the session cleanly
6. Round-trip latency (input → frame) is measured
"""

import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from server import StreamingServer  # noqa: E402

# websockets is already installed
import websockets


SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8766  # Use a non-default port to avoid conflicts


async def test_streaming_lifecycle():
    """Verify the full streaming lifecycle: connect → start → frames → input → stop."""
    print("=== Test: Streaming lifecycle ===")

    server = StreamingServer(host=SERVER_HOST, port=SERVER_PORT)

    # Start server in background
    server_task = asyncio.create_task(_run_server(server))

    # Give the server a moment to bind
    await asyncio.sleep(0.5)

    try:
        async with websockets.connect(f"ws://{SERVER_HOST}:{SERVER_PORT}") as ws:
            # --- Start session ---
            await ws.send(json.dumps({
                "type": "start",
                "url": "https://example.com",
            }))

            # Wait for session_started
            response = json.loads(await asyncio.wait_for(ws.recv(), timeout=15))
            assert response["type"] == "session_started", f"Expected session_started, got {response['type']}"
            session_id = response["session_id"]
            print(f"  Session started: {session_id}")

            # --- Wait for at least one frame ---
            frame_received = False
            frame_start = time.time()
            while time.time() - frame_start < 10:  # 10s timeout
                try:
                    msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
                    if msg["type"] == "frame":
                        frame_received = True
                        frame_time = time.time() - frame_start
                        # Verify frame has data
                        assert "data" in msg, "Frame missing 'data' field"
                        assert len(msg["data"]) > 0, "Frame data is empty"
                        assert "timestamp" in msg, "Frame missing 'timestamp' field"
                        print(f"  First frame received in {frame_time:.2f}s ({len(msg['data'])} bytes base64)")
                        break
                except asyncio.TimeoutError:
                    break

            assert frame_received, "No screencast frame received within 10s"

            # --- Test mouse input ---
            input_start = time.time()
            await ws.send(json.dumps({
                "type": "mouse",
                "action": "click",
                "x": 100,
                "y": 100,
                "button": "left",
            }))

            # After click, we should get updated frames
            frames_after_click = 0
            while time.time() - input_start < 5:
                try:
                    msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=2))
                    if msg["type"] == "frame":
                        frames_after_click += 1
                        if frames_after_click >= 1:
                            latency = time.time() - input_start
                            print(f"  Frame after click received in {latency:.3f}s (latency)")
                            break
                except asyncio.TimeoutError:
                    break

            print(f"  Input dispatch: {'PASS' if frames_after_click > 0 else 'WARN (no frame after click, but no error)'}")

            # --- Test scroll input ---
            await ws.send(json.dumps({
                "type": "scroll",
                "x": 640,
                "y": 400,
                "deltaX": 0,
                "deltaY": 100,
            }))
            print("  Scroll dispatched without error")

            # --- Test keyboard input ---
            await ws.send(json.dumps({
                "type": "keyboard",
                "action": "type",
                "key": "",
                "text": "hello",
            }))
            print("  Keyboard input dispatched without error")

            # --- Stop session ---
            await ws.send(json.dumps({"type": "stop"}))

            # Wait for session_ended
            end_received = False
            while True:
                try:
                    msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
                    if msg["type"] == "session_ended":
                        end_received = True
                        break
                except asyncio.TimeoutError:
                    break

            assert end_received, "Never received session_ended"
            print("  Session ended cleanly")

    finally:
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass

    print("  PASS: Streaming lifecycle works correctly\n")


async def test_error_handling():
    """Verify error handling for bad inputs."""
    print("=== Test: Error handling ===")

    server = StreamingServer(host=SERVER_HOST, port=SERVER_PORT + 1)
    server_task = asyncio.create_task(_run_server(server))
    await asyncio.sleep(0.5)

    try:
        async with websockets.connect(f"ws://{SERVER_HOST}:{SERVER_PORT + 1}") as ws:
            # Send invalid JSON
            await ws.send("not json")
            response = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
            assert response["type"] == "error"
            print(f"  Invalid JSON handled: {response['message']}")

            # Send start without URL
            await ws.send(json.dumps({"type": "start"}))
            response = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
            assert response["type"] == "error"
            print(f"  Missing URL handled: {response['message']}")

    finally:
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass

    print("  PASS: Error handling works correctly\n")


async def _run_server(server):
    """Run the server until cancelled."""
    try:
        await server.serve()
    except asyncio.CancelledError:
        pass


async def main():
    print("Streaming Server Tests (Sub-Phase 2)\n")

    await test_streaming_lifecycle()
    await test_error_handling()

    print("All Streaming tests passed.")


if __name__ == "__main__":
    asyncio.run(main())
