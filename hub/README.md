# MisakaHub

> Lightweight sync coordinator + knowledge graph + arbitration manager.
> Reuses Hermes Agent's Feishu bot credentials so hub notifications land
> in the same chat the operator already uses.

`hub/misaka_hub.py` does three things:

1. **Periodic sync** of lesson graphs across nodes (`SyncScheduler`).
2. **Conflict detection** — creates a GitHub Issue instead of a Feishu card.
3. **Optional notifications** to Discord / Slack / Email / **Feishu**.

## Quick start

```bash
# Optional: reuse Hermes' Feishu credentials (same bot, same chat).
# Either export them yourself, or `source` the same env file Hermes uses:
source ~/.hermes/.env

# Run with the bundled example config:
python3 -m hub.misaka_hub
```

The hub reads `./hub/config.yaml`. See `hub/config.yaml.example` for the
schema — all credential values should be **environment variables**, not
literal strings in YAML.

## Notification channels

| Channel | Required config | Mode |
|---|---|---|
| Discord | `notifier.discord.webhook_url` | Webhook |
| Slack | `notifier.slack.webhook_url` | Webhook |
| Email | `EMAIL_SMTP_HOST` / `EMAIL_SMTP_PORT` / `EMAIL_SENDER` / `EMAIL_PASSWORD` / `EMAIL_RECIPIENT` | SMTP |
| **Feishu** | `FEISHU_APP_ID` + `FEISHU_APP_SECRET` (+ optional `FEISHU_HOME_CHANNEL`) | OpenAPI push |

Enable Feishu explicitly under `notifier.feishu.enabled: true` (or simply
export `FEISHU_APP_ID` and the hub will auto-wire it). See
`hub/sync/feishu_notifier.py` for the implementation; it uses the same
OpenAPI flow as `~/.hermes/hermes-agent/plugins/platforms/feishu/` so
messages look identical to a Hermes reply.

## Tests

```bash
python3 -m pytest tests/test_federation.py tests/test_token_manager_nokeyring.py tests/test_feishu_notifier.py tests/test_hub_smoke.py -q
```

## Status

This module is no longer marked "legacy" — it is the implementation that
the v2 refactor (`lessons/contrib/misakanet-refactor-v2-review.md`)
trimmed down from 363 lines to 172. Earlier live-A2A and inbound-WS
components were intentionally archived to `archive/dead/`; the design
rationale is in that refactor lesson.
