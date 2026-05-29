# The Agent Room — 8-bit visualization

A pixel-art "office" that visualizes the marketing agents (Tess 🔭, Carla ✍️,
Edu 📐, Pablo 📤) live and on replay, reading from the observatory **event log**
(`GET /api/events` for history + `GET /api/events/stream` SSE for live).

## Origin & licensing

This is a **fork of [pixel-agents](https://github.com/pixel-agents-hq/pixel-agents)**
(MIT, © 2026 Pablo De Lucca — see `LICENSE-pixel-agents.txt`). We kept its
Canvas2D renderer, character state machine, and office/asset system, and
**replaced its data source**: instead of watching Claude Code JSONL transcripts,
we feed it our own event stream.

Character sprites are based on JIK-A-4's **"MetroCity" top-down character pack**
([itch.io](https://jik-a-4.itch.io/metrocity-free-topdown-character-pack)),
released under **CC0** (public domain).

## What we changed

- `webview-ui/src/transport/sseTransport.ts` — new transport that loads assets,
  creates the fixed cast, replays `/api/events`, and streams `/api/events/stream`.
- `webview-ui/src/transport/eventTranslate.ts` — maps our `event_type`s to the
  renderer's tool/animation messages (Tess/Edu "read", Carla/Pablo "type";
  `pablo.published` → ✅ waiting bubble).
- `webview-ui/src/transport/index.ts` — browser runtime now uses `SseTransport`.
- `webview-ui/src/browserMock.ts` — exposed `loadAssets()` + `assetLoadMessages()`.

The office engine (`webview-ui/src/office/`) and `useExtensionMessages.ts` are
**unmodified** — everything flows through `transport.onMessage`.

## Build & serve

```bash
cd webview-ui
npm install
npm run build      # → ../dist/webview (committed; served by FastAPI at /room)
```

The observatory mounts `room/dist/webview` at **`/room`** (StaticFiles) when present.
Open `http://<host>:8400/room` over Tailscale.
