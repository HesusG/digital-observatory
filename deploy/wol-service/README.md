# wol-service

A ~50-line stdlib-only HTTP server that broadcasts a Wake-on-LAN magic packet
on demand. Runs alongside the observatory on nano-spud so that scheduled
workflows can wake d3r-ser before they make Ollama calls.

## Why a separate container?

- The observatory and n8n containers use Docker's bridge networking. Outgoing
  traffic gets NAT'd, and broadcast packets are dropped by the bridge. They
  literally cannot deliver a WOL packet to 192.168.1.255.
- `network_mode: host` would fix that, but applying it to the whole
  observatory or n8n stack is invasive and changes their port-binding model.
- A tiny single-purpose sidecar with `network_mode: host` keeps the rest of
  the stack unchanged.

## Setup

```bash
cd /home/d3r/repos/digital-observatory/deploy/wol-service
cp .env.example .env             # adjust WOL_MAC / WOL_BROADCAST if needed
docker compose up -d
docker compose logs -f wol       # should print "wol-service listening on ..."
```

## Test from nano-spud

```bash
curl http://localhost:9999/healthz
# {"status":"ok","default_mac":"70:70:fc:04:ed:fa","broadcast":"192.168.1.255"}

curl -X POST http://localhost:9999/wake
# {"status":"sent","mac":"70:70:fc:04:ed:fa","broadcast":"192.168.1.255"}
```

Within ~15 seconds of POST /wake, d3r-ser should be reachable on Tailscale and
Ollama should be answering on port 11434.

## How the observatory uses it

`observatory/app.py` exposes `POST /api/wake-ollama` which:

1. Calls `POST http://<wol_service_host>:9999/wake`.
2. Polls `${OLLAMA_BASE_URL}/api/tags` every 2 seconds for up to 30 seconds.
3. Returns 200 the moment Ollama responds, or 504 if the timeout elapses.

n8n workflows that need Ollama call `/api/wake-ollama` first, then proceed to
`/api/pipeline/run` or `/api/content/draft`. If Ollama was already awake, the
call is a fast no-op (<200 ms).
