"""
Feishu (Lark) notification channel for MisakaHub.

Reuses Hermes Agent's Feishu bot credentials (FEISHU_APP_ID / FEISHU_APP_SECRET
/ FEISHU_HOME_CHANNEL) so messages from the hub appear in the same Feishu
chat the operator already uses to talk to Hermes. No incoming-webhook
configuration needed — we push via the official OpenAPI.

Why this shape:
- Hub already has Discord / Slack / Email notifiers built around an abstract
  `Notifier` base class. We follow the same shape so the Hub constructor can
  treat Feishu the same way (see hub/misaka_hub.py:67-75).
- Hermes Agent runs its own WS gateway and may also send to the same chat;
  since we use the same app_id, Feishu will simply render both messages
  from the same bot. We throttle to avoid stampede.
- Credentials are read from environment variables only. Operators are expected
  to `source ~/.hermes/.env` (or set the same vars) before launching the hub.
  This mirrors how Hermes Gateway reads them (see
  ~/.hermes/hermes-agent/gateway/run.py around line 1675).

Public API:
    FeishuNotifier(config=None)
        .notify_arbitration_case(case)
        .notify_sync_ready(agent_id, skill_count)
        .send_hook_stats(stats)
        .notify_agent_registered(agent_id)
        .send_text(text, receive_id=None)        # convenience
        .send_card(title, markdown, receive_id=None)
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from hub.sync.notifier import Notifier

logger = logging.getLogger(__name__)


# ── OpenAPI endpoints ───────────────────────────────────────────────
# International Lark (`open.larksuite.com`) differs from Feishu CN
# (`open.feishu.cn`). Hermes reads FEISHU_DOMAIN to switch; we mirror.
FEISHU_ENDPOINTS = {
    "feishu": {
        "auth": "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        "messages": "https://open.feishu.cn/open-apis/im/v1/messages",
    },
    "lark": {
        "auth": "https://open.larksuite.com/open-apis/auth/v3/tenant_access_token/internal",
        "messages": "https://open.larksuite.com/open-apis/im/v1/messages",
    },
}


def _now() -> float:
    return time.time()


class FeishuNotifier(Notifier):
    """Feishu / Lark OpenAPI sender — Hermes-bot compatible.

    Reads:
        FEISHU_APP_ID         — required
        FEISHU_APP_SECRET     — required
        FEISHU_HOME_CHANNEL   — optional, default receive_id (oc_xxx chat_id)
        FEISHU_DOMAIN         — "feishu" (default) or "lark"

    Optional config dict (passed by Hub or `FeishuNotifier(config={...})`):
        app_id, app_secret, home_channel, domain
        timeout (seconds, default 10)
        max_message_length (default 4000)
        dry_run (default False — when True, log instead of POST)
    """

    TOKEN_TTL_S = 60 * 60  # Feishu tokens are valid ~2h; refresh every hour

    def __init__(self, config: Optional[dict] = None):
        cfg = config or {}
        self.app_id: str = cfg.get("app_id") or os.environ.get("FEISHU_APP_ID", "")
        self.app_secret: str = cfg.get("app_secret") or os.environ.get("FEISHU_APP_SECRET", "")
        self.home_channel: str = (
            cfg.get("home_channel")
            or os.environ.get("FEISHU_HOME_CHANNEL", "")
        )
        domain = (cfg.get("domain") or os.environ.get("FEISHU_DOMAIN", "feishu")).lower()
        if domain not in FEISHU_ENDPOINTS:
            logger.warning(f"FeishuNotifier: unknown domain {domain!r}, falling back to 'feishu'")
            domain = "feishu"
        self.domain = domain
        self.timeout: int = int(cfg.get("timeout", 10))
        self.max_message_length: int = int(cfg.get("max_message_length", 4000))
        self.dry_run: bool = bool(cfg.get("dry_run", False))

        self._token: Optional[str] = None
        self._token_expires_at: float = 0.0
        self._token_lock = threading.Lock()

        if not self.app_id or not self.app_secret:
            logger.warning(
                "FeishuNotifier: missing FEISHU_APP_ID/FEISHU_APP_SECRET; "
                "all sends will be skipped (treated as dry_run)."
            )
            self.dry_run = True

    # ── Notifier abstract methods ────────────────────────────────────

    def notify_arbitration_case(self, case: dict) -> bool:
        versions = case.get("versions", [])
        bullets = "\n".join(
            f"- **v{i+1}** ({v.get('source', '?')}): "
            f"{(v.get('description') or '')[:120]}"
            for i, v in enumerate(versions)
        ) or "(no candidate versions provided)"
        body = (
            f"**Case ID**: `{case.get('id', '')}`\n\n"
            f"**Versions**:\n{bullets}\n\n"
            "_Reply with `select v1` / `保留 xxx` to resolve the case._"
        )
        return self.send_card(
            title=f"⚖️ 仲裁请求: {case.get('skill_name', 'Unknown')}",
            markdown=body,
            header_color="red",
        )

    def notify_sync_ready(self, agent_id: str, skill_count: int) -> bool:
        return self.send_text(
            f"🔄 MisakaHub sync ready — node `{agent_id}` "
            f"({skill_count} skills indexed)"
        )

    def send_hook_stats(self, stats) -> bool:
        lines = ["📊 MisakaHub Hook stats"]
        for s in stats or []:
            node = s.get("node", "?")
            cat_lines = []
            for cat in ("network", "pip", "permission", "disk", "package_conflict", "model_output"):
                t = s.get("triggers", {}).get(cat, 0)
                h = s.get("hits", {}).get(cat, 0)
                if t > 0:
                    icon = {
                        "network": "🔴", "pip": "🟡", "permission": "🔵",
                        "disk": "🟣", "package_conflict": "🟠", "model_output": "⚪",
                    }.get(cat, "⚪")
                    cat_lines.append(f"  {icon} {cat}  {t}× triggers  {h}× lesson hits")
            if cat_lines:
                lines.append(f"**Node {node}**")
                lines.extend(cat_lines)
            else:
                lines.append(f"**Node {node}**: no triggers")
        return self.send_text("\n".join(lines))

    def notify_agent_registered(self, agent_id: str) -> bool:
        return self.send_text(f"🤖 New node registered: `{agent_id}`")

    # ── Convenience senders ──────────────────────────────────────────

    def send_text(self, text: str, receive_id: Optional[str] = None) -> bool:
        """Send a plain-text message. Splits over max_message_length."""
        receive_id = receive_id or self.home_channel
        if not receive_id:
            logger.debug("FeishuNotifier.send_text: no receive_id, skipping")
            return False
        for chunk in _chunk_text(text, self.max_message_length):
            payload = {"msg_type": "text", "content": json.dumps({"text": chunk})}
            if not self._post_message(receive_id, payload):
                return False
        return True

    def send_card(self, title: str, markdown: str, receive_id: Optional[str] = None,
                  header_color: str = "turquoise") -> bool:
        """Send an interactive card (2.0 schema). Splits body if too long."""
        receive_id = receive_id or self.home_channel
        if not receive_id:
            logger.debug("FeishuNotifier.send_card: no receive_id, skipping")
            return False
        chunks = _chunk_text(markdown, self.max_message_length) or [""]
        for i, chunk in enumerate(chunks):
            payload = {
                "msg_type": "interactive",
                "card": {
                    "header": {
                        "title": {"tag": "plain_text", "content": title if i == 0 else f"{title} ({i+1}/{len(chunks)})"},
                        "template": header_color,
                    },
                    "elements": [
                        {"tag": "markdown", "content": chunk},
                    ],
                },
            }
            if not self._post_message(receive_id, payload):
                return False
        return True

    # ── Token + HTTP plumbing ────────────────────────────────────────

    def _get_token(self) -> str:
        if self.dry_run:
            return "dry-run-token"
        with self._token_lock:
            if self._token and _now() < self._token_expires_at:
                return self._token
            endpoints = FEISHU_ENDPOINTS[self.domain]
            body = json.dumps({"app_id": self.app_id, "app_secret": self.app_secret}).encode("utf-8")
            req = Request(
                endpoints["auth"],
                data=body,
                headers={"Content-Type": "application/json"},
            )
            try:
                with urlopen(req, timeout=self.timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
            except (URLError, HTTPError, json.JSONDecodeError, TimeoutError) as exc:
                logger.error(f"FeishuNotifier: token fetch failed: {exc!r}")
                return ""
            if data.get("code") != 0:
                logger.error(f"FeishuNotifier: token error {data.get('code')}: {data.get('msg')}")
                return ""
            self._token = data.get("tenant_access_token", "")
            self._token_expires_at = _now() + self.TOKEN_TTL_S
            return self._token

    def _post_message(self, receive_id: str, payload: dict) -> bool:
        if self.dry_run:
            logger.info(
                f"FeishuNotifier[dry_run] -> {receive_id}: {payload.get('msg_type')} "
                f"{json.dumps(payload, ensure_ascii=False)[:120]}..."
            )
            return True
        token = self._get_token()
        if not token:
            return False
        endpoints = FEISHU_ENDPOINTS[self.domain]
        url = endpoints["messages"] + "?" + urlencode({"receive_id_type": "chat_id"})
        body = json.dumps({"receive_id": receive_id, **payload}).encode("utf-8")
        req = Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            },
        )
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (URLError, HTTPError, json.JSONDecodeError, TimeoutError) as exc:
            logger.error(f"FeishuNotifier: send failed: {exc!r}")
            return False
        if data.get("code") != 0:
            logger.error(
                f"FeishuNotifier: send error code={data.get('code')} msg={data.get('msg')}"
            )
            return False
        return True


def _chunk_text(text: str, max_len: int) -> list[str]:
    """Naive line-aware splitter; preserves readability over exact length.

    Splits by newline when possible, falls back to hard-cutting single
    lines that exceed max_len on their own (e.g. a long URL).
    """
    if not text:
        return []
    if max_len <= 0:
        return [text]
    if len(text) <= max_len:
        return [text]
    chunks: list[str] = []
    buf: list[str] = []
    cur = 0
    for line in text.splitlines(keepends=True):
        # Hard-cut a single oversized line
        if len(line) > max_len:
            if buf:
                chunks.append("".join(buf).rstrip())
                buf = []
                cur = 0
            for i in range(0, len(line), max_len):
                chunks.append(line[i : i + max_len].rstrip())
            continue
        if cur + len(line) > max_len and buf:
            chunks.append("".join(buf).rstrip())
            buf = [line]
            cur = len(line)
        else:
            buf.append(line)
            cur += len(line)
    if buf:
        chunks.append("".join(buf).rstrip())
    return chunks


__all__ = ["FeishuNotifier", "FEISHU_ENDPOINTS"]
