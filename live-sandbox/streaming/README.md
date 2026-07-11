# Live Screen Streaming (`live-sandbox/streaming`)

Manages streaming the interactive, containerized browser viewport back to
the user's frontend in real time, and relaying user input events back into
the sandboxed page.

## Modules

### `server.py`
`StreamingServer` — WebSocket server (default `ws://127.0.0.1:8765`):

- **Session management**: accepts `{ "type": "start", "url": "..." }` to
  create a `Session` from `orchestration/session.py`, and `{ "type": "stop" }`
  to tear it down.
- **Screencast**: starts CDP `Page.startScreencast` on the Playwright page,
  relays JPEG frames as base64 over WebSocket in
  `{ "type": "frame", "data": "...", "timestamp": ... }` messages.
- **Input relay**: receives mouse (`click`, `move`, `down`, `up`), keyboard
  (`down`, `up`, `type`), and scroll events from the frontend, dispatches
  them via CDP `Input.dispatchMouseEvent` / `Input.dispatchKeyEvent` /
  `Input.insertText`.
- **Simulation results**: `broadcast_simulation_result(result)` sends
  `{ "type": "simulation_result", "data": { ... } }` to the connected client
  (used by the interceptor in Sub-Phase 4).
- **Error handling**: invalid JSON and missing fields return structured error
  messages.

## Performance

Tested latency (against `https://example.com`):
- First frame: ~10ms after session start
- Input → frame round-trip: ~25ms

Both are well below the ~100ms threshold for "feels live" interaction.

## Dependency on `sandbox/`

No direct dependency on `sandbox/` code. Coordinates with `interceptor/`
to display wallet impact overlays once `sandbox/` returns simulation results.

## Tests

```sh
py -3.14 live-sandbox/streaming/test_stream.py
```

Verifies:
- Server starts and accepts WebSocket connections
- Session lifecycle (start → frames → input → stop)
- At least one screencast frame received
- Mouse/keyboard/scroll input dispatched without error
- Input latency measured
- Error handling for bad JSON and missing fields
