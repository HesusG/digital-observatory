# Postiz on nano-spud

Self-hosted social-media publisher used by the marketing-team n8n workflows.

## First-time deploy

```bash
# On nano-spud:
cd /home/d3r/repos/digital-observatory/deploy/postiz

# Generate secrets and copy to .env
cp .env.example .env
sed -i "s/changeme-base64-48/$(openssl rand -base64 48)/" .env
sed -i "s/changeme-hex-24/$(openssl rand -hex 24)/" .env

docker compose up -d
docker compose logs -f postiz   # wait for "ready" line
```

Web UI: bind is on `127.0.0.1:5000` for safety. Reach over Tailscale via SSH tunnel:

```bash
# From Fedora:
ssh -L 5000:127.0.0.1:5000 nano-spud
# Then open http://localhost:5000 in your browser.
```

(For permanent Tailscale-network access, add an nginx reverse proxy or change the bind to `100.84.156.15:5000`.)

## Connecting socials — order of operations

1. **Bluesky** — Postiz UI → Integrations → Bluesky. Use a Bluesky app password (`Settings → App passwords` on bsky.app). Instant.
2. **X (Twitter)** — apply for a free dev account at `https://developer.x.com/`. ~hours for the basic tier. Get API key + secret + bearer token. Paste into Postiz.
3. **LinkedIn** — register a LinkedIn app at `https://www.linkedin.com/developers/`. Request the `w_member_social` scope. **App review takes days to weeks.** Do this in parallel with steps 1-2; come back when it's approved.

## n8n wiring

After connecting at least one integration:

1. In Postiz UI, copy each integration's `id` (visible in the Integrations panel URL or via `GET /api/public/v1/integrations`).
2. Generate a Postiz API key (UI: Settings → API Keys).
3. In n8n, set environment variables:
   - `POSTIZ_API_KEY=<the key>`
4. Edit `deploy/n8n/marketing-team-callback.json` to replace `PLACEHOLDER_POSTIZ_INTEGRATION_ID` with the real integration ID for each connected platform. Add one HTTP node per platform.

## Resource budget

- Postiz app: ~500MB RAM, light CPU.
- Postgres: ~150MB RAM.
- Redis: ~50MB RAM.

Total: well under 1GB. Fine alongside the observatory + chromadb on nano-spud.
