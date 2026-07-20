# AusGov Budget Tracker — Backend Cloudflare Worker

A plain reverse-proxy Worker in front of the self-hosted FastAPI origin
(`ausgov-budget-origin.vibefactory.app`, a Docker container behind the
shared vibefactory Cloudflare Tunnel — see `../../docker-compose.vibefactory.yml`).

No Durable Objects, no KV, no secrets — the API is stateless and fully
public, so there's no edge logic to run here beyond giving the backend a
stable `ausgov-budget-api.vibefactory.app` hostname.

## Deploy

```bash
npm install
npm run deploy:vibefactory
```

Requires `wrangler` to be authenticated (`wrangler login` or
`CLOUDFLARE_API_TOKEN` in the environment) and the origin's tunnel ingress
entry (`ausgov-budget-origin.vibefactory.app` → `127.0.0.1:8010`) to already
be live in `/etc/cloudflared/vibefactory.yml` — otherwise the Worker will
deploy successfully but every request will fail to reach the origin.

## Local dev

```bash
npm run dev
```
