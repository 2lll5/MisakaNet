# MisakaNet Deployment Guide

> Production deployment paths for MisakaNet services — from single-node CLI to federated Hub.

---

## Quick Start: Local Development

```bash
# Clone and install
git clone https://github.com/Ikalus1988/MisakaNet.git
cd MisakaNet
pip install -e ".[hub]"

# Verify
python3 search_knowledge.py "python docker" --domain devops
```

**Requirements:** Python 3.10+, git, 200MB free disk.

---

## Deployment Paths Overview

| Path | Use Case | Complexity | Scale |
|------|----------|-----------|-------|
| **Local CLI** | Individual agent knowledge retrieval | Minimal | 1 node |
| **MCP Server (stdio)** | Claude Code / Cursor integration | Low | 1 user |
| **MCP Server (HTTP)** | Multi-client team access | Medium | 1–50 users |
| **Docker Container** | Isolated, reproducible deployment | Medium | Any |
| **Cloudflare Workers** | Global edge deployment (dashboard) | Medium | Unlimited |
| **Hub (Standalone)** | Multi-node sync + knowledge graph | High | 10–1000 nodes |
| **Hub (Federation)** | Cross-org knowledge sharing | High | N organizations |

---

## 1. Docker Deployment

### Build

```bash
docker build -t misakanet:latest .
```

The `Dockerfile` (Python 3.11-slim) bundles:
- MCP server (stdio entrypoint)
- Search engine + lessons
- Contribution tools
- Usage meter

### Run

```bash
# MCP server (default CMD)
docker run -v $(pwd)/lessons:/app/lessons misakanet:latest

# Interactive search
docker run -it --entrypoint python3 misakanet:latest search_knowledge.py "query"

# Custom port for HTTP MCP
docker run -p 8080:8080 --entrypoint python3 \
  misakanet:latest scripts/mcp_http_server.py --port 8080
```

### Docker Compose (Hub + MCP)

```yaml
version: "3.8"
services:
  misakanet-mcp:
    build: .
    ports:
      - "8080:8080"
    entrypoint: python3
    command: scripts/mcp_http_server.py --port 8080
    volumes:
      - ./lessons:/app/lessons
      - ./data:/app/data

  misakanet-hub:
    build: .
    entrypoint: python3
    command: hub/misaka_hub.py
    volumes:
      - ./lessons:/app/lessons
      - ./data:/app/data
    environment:
      - DISCORD_WEBHOOK_URL=${DISCORD_WEBHOOK_URL}
      - GITHUB_TOKEN=${GITHUB_TOKEN}
```

### Volume Mounts

| Path | Purpose | Required |
|------|---------|----------|
| `/app/lessons` | Lesson knowledge base | Yes |
| `/app/data` | SAG-Lite index, usage DB | Recommended |
| `/app/scripts` | Tool scripts | No (included) |

---

## 2. Cloudflare Workers Deployment

The dashboard (`docs/index.html`) is deployed as a Cloudflare Workers static site.

### Prerequisites

```bash
npm install -g wrangler
```

### Configuration (`wrangler.jsonc`)

```jsonc
{
  "name": "misakanet-web",
  "compatibility_date": "2026-07-04",
  "assets": { "directory": "docs" },
  "compatibility_flags": ["nodejs_compat"],
  "kv_namespaces": [
    { "binding": "MISAKANET_KV", "id": "YOUR_KV_NAMESPACE_ID" }
  ]
}
```

### Deploy

```bash
# From repo root
cd web
npm install
npx wrangler deploy

# Or from repo root with wrangler.jsonc at root
npx wrangler deploy
```

### KV Namespace Setup

```bash
npx wrangler kv:namespace create MISAKANET_KV
# Update wrangler.jsonc with the returned ID
```

### CI/CD (`.github/workflows/deploy-worker.yml`)

The `deploy-worker.yml` workflow auto-deploys on push to `main` when `docs/` or `web/` files change. Requires:

| Secret | Purpose |
|--------|---------|
| `CLOUDFLARE_API_TOKEN` | API token with Workers edit permission |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare account identifier |

---

## 3. MCP Server Deployment

### 3.1 Local (stdio) — for Claude Code

Add to `claude_desktop_config.json` or `.claude/settings.json`:

```json
{
  "mcpServers": {
    "misakanet": {
      "command": "python3",
      "args": [
        "/absolute/path/to/MisakaNet/scripts/mcp_server.py"
      ]
    }
  }
}
```

### 3.2 Remote (HTTP) — for Team Access

```bash
# Start server
python3 scripts/mcp_http_server.py --port 8080

# Production: use systemd or supervisor
# Example systemd unit: /etc/systemd/system/misakanet-mcp.service
```

**systemd Unit:**

```ini
[Unit]
Description=MisakaNet MCP HTTP Server
After=network.target

[Service]
Type=simple
User=misakanet
WorkingDirectory=/opt/MisakaNet
ExecStart=/usr/bin/python3 scripts/mcp_http_server.py --port 8080
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 3.3 Behind Reverse Proxy (nginx)

```nginx
location /mcp {
    proxy_pass http://127.0.0.1:8080/mcp;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_read_timeout 86400s;
}
```

---

## 4. Hub Deployment

### 4.1 Standalone Sync Scheduler

```bash
# Install dependencies
pip install -e ".[hub]"

# Start periodic sync (runs git fetch + knowledge graph rebuild on schedule)
python3 hub/misaka_hub.py
```

### 4.2 Master Mode

```bash
# Start master API
python3 -m hub.master.master_api --port 9000

# CLI control
python3 -m hub.master.master_cli status
python3 -m hub.master.master_cli nodes list
python3 -m hub.master.master_cli sync trigger
```

### 4.3 Federation Setup

```bash
# Generate shared secret
python3 -c "import secrets; print(secrets.token_hex(32))"

# Configure nodes
export FEDERATION_SECRET="<generated-secret>"
export FEDERATION_PEERS="https://peer1.example.com,https://peer2.example.com"
```

### 4.4 Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GITHUB_TOKEN` | Yes* | — | GitHub PAT for API operations |
| `DISCORD_WEBHOOK_URL` | No | — | Discord notification webhook |
| `SLACK_WEBHOOK_URL` | No | — | Slack notification webhook |
| `FEISHU_WEBHOOK_URL` | No | — | Feishu/Lark notification webhook |
| `EMAIL_SMTP_HOST` | No | — | SMTP server address |
| `EMAIL_SMTP_PORT` | No | 587 | SMTP port |
| `EMAIL_FROM` | No | — | Sender address |
| `EMAIL_TO` | No | — | Recipient address |
| `FEDERATION_SECRET` | No** | — | HMAC shared secret for federation |
| `FEDERATION_PEERS` | No** | — | Comma-separated peer URLs |
| `CLOUDFLARE_API_TOKEN` | No*** | — | CF Workers deploy token |
| `CLOUDFLARE_ACCOUNT_ID` | No*** | — | CF account ID |

> \* Required for contribution API and Hub. Not required for read-only search.
> \*\* Required only for Hub Federation mode.
> \*\*\* Required only for Cloudflare Workers deployment.

---

## 5. Monitoring & Health Checks

### Built-in Health Endpoints

```bash
# Site health check
python3 scripts/site_health_check.py

# Worker secrets audit
python3 scripts/check_worker_secrets.py

# Node status
python3 scripts/node_status.py
```

### Logging

All components use Python's `logging` module. Set `LOG_LEVEL=DEBUG` for verbose output:

```bash
LOG_LEVEL=DEBUG python3 hub/misaka_hub.py
```

### Heartbeat

The `scripts/heartbeat.sh` script can be wired into cron for periodic health pings:

```bash
# crontab example — every 5 minutes
*/5 * * * * /opt/MisakaNet/scripts/heartbeat.sh
```

---

## 6. CI/CD Pipeline (`pr-shape-guard.yml`)

The PR Shape Guard (`pr-shape-guard.yml`) enforces deployment safety:

| Check | What It Verifies |
|-------|-----------------|
| **File deletion guard** | PRs must not delete existing files |
| **Directory structure** | New files must follow repo conventions |
| **DCO compliance** | Every commit must have `Signed-off-by:` |
| **No unrelated files** | PR scope must match issue acceptance criteria |

---

## 7. Security Considerations

### For Production Deployments

1. **Never expose MCP HTTP server directly to the internet** — use a reverse proxy with authentication
2. **Rotate `FEDERATION_SECRET` regularly** — every 90 days minimum
3. **Use read-only GitHub tokens** for search-only deployments
4. **Limit KV namespace permissions** in Cloudflare to least privilege
5. **Audit webhook URLs** — all notifications go through external services
6. **Pin Docker base images** by SHA digest in production

### Secrets Management

```bash
# Never commit secrets — use environment variables or a vault
export $(grep -v '^#' .env | xargs)  # Load from .env (not tracked in git)
```

---

## 8. Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `ImportError: misakanet_core` | Missing dependency | `pip install misakanet-core` |
| MCP connection refused | Server not running or wrong port | Check `lsof -i :8080` |
| Search returns 0 results | Index not built | Run `python3 search_knowledge.py "" --domain any` to warm cache |
| Docker build fails | Outdated base image | `docker pull python:3.11-slim` first |
| CF deploy 401 | Expired API token | Rotate `CLOUDFLARE_API_TOKEN` in repo secrets |
| Hub sync stuck | Git merge conflict | Resolve manually in `lessons/` then re-run |
