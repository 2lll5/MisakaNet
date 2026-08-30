"""Tests for hub/sync/feishu_notifier.py.

Covers the operator-facing contract:

  1. Default constructor with no credentials -> dry_run, no crash.
  2. Constructor reads FEISHU_APP_ID / FEISHU_APP_SECRET / FEISHU_HOME_CHANNEL
     from environment when no config is passed.
  3. Token acquisition is **skipped** in dry_run (no real HTTP).
  4. The four Notifier abstract methods succeed in dry_run and return
     the boolean contract the Hub expects.
  5. `send_text` / `send_card` chunk long payloads over max_message_length.
  6. send_text returns False when no receive_id is configured (early exit,
     not an exception).
  7. The international Lark endpoint set is honored when FEISHU_DOMAIN=lark.
  8. The urlopen call for token + send uses the right URLs.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from unittest import mock

# Ensure repo root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hub.sync.feishu_notifier import (
    FEISHU_ENDPOINTS,
    FeishuNotifier,
    _chunk_text,
)


class TestFeishuNotifierDryRun(unittest.TestCase):
    """Behaves like a notifier but never reaches the network."""

    def test_no_creds_auto_dry_run(self):
        n = FeishuNotifier(config={"app_id": "", "app_secret": ""})
        self.assertTrue(n.dry_run)
        # No receive_id => graceful False (caller is expected to skip)
        self.assertFalse(n.send_text("hi"))
        # Token fetch in dry_run returns the placeholder, no HTTP
        self.assertEqual(n._get_token(), "dry-run-token")

    def test_explicit_dry_run_with_home_channel(self):
        n = FeishuNotifier(
            config={"dry_run": True, "home_channel": "oc_test_chat_001"}
        )
        self.assertTrue(n.dry_run)
        self.assertTrue(n.send_text("hello"))
        self.assertTrue(n.send_card("Title", "body **bold**", header_color="blue"))
        self.assertTrue(n.notify_sync_ready("node-x", 42))
        self.assertTrue(n.notify_agent_registered("node-y"))
        self.assertTrue(
            n.notify_arbitration_case(
                {
                    "id": "ARB-001",
                    "skill_name": "feishu-api",
                    "versions": [
                        {"source": "a", "description": "v1"},
                        {"source": "b", "description": "v2"},
                    ],
                }
            )
        )
        self.assertTrue(
            n.send_hook_stats(
                [
                    {
                        "node": "n1",
                        "triggers": {"pip": 3, "network": 1},
                        "hits": {"pip": 1},
                    }
                ]
            )
        )

    def test_hook_stats_handles_empty(self):
        n = FeishuNotifier(config={"dry_run": True, "home_channel": "oc_x"})
        self.assertTrue(n.send_hook_stats([]))


class TestFeishuNotifierEnv(unittest.TestCase):
    """Constructor honors env vars (the Hermes reuse contract)."""

    def setUp(self):
        self._saved = {}
        for k in ("FEISHU_APP_ID", "FEISHU_APP_SECRET", "FEISHU_HOME_CHANNEL", "FEISHU_DOMAIN"):
            self._saved[k] = os.environ.pop(k, None)

    def tearDown(self):
        for k, v in self._saved.items():
            if v is not None:
                os.environ[k] = v
            else:
                os.environ.pop(k, None)

    def test_env_picked_up_when_no_config(self):
        os.environ["FEISHU_APP_ID"] = "cli_env_app"
        os.environ["FEISHU_APP_SECRET"] = "env_secret"
        os.environ["FEISHU_HOME_CHANNEL"] = "oc_env_channel"
        os.environ["FEISHU_DOMAIN"] = "lark"
        n = FeishuNotifier()
        self.assertEqual(n.app_id, "cli_env_app")
        self.assertEqual(n.app_secret, "env_secret")
        self.assertEqual(n.home_channel, "oc_env_channel")
        self.assertEqual(n.domain, "lark")

    def test_config_overrides_env(self):
        os.environ["FEISHU_APP_ID"] = "env_id"
        n = FeishuNotifier(config={"app_id": "config_id", "dry_run": True})
        self.assertEqual(n.app_id, "config_id")


class TestChunkText(unittest.TestCase):
    def test_short_text_passthrough(self):
        self.assertEqual(_chunk_text("hello", 100), ["hello"])

    def test_empty(self):
        self.assertEqual(_chunk_text("", 100), [])

    def test_hard_cut_single_line(self):
        parts = _chunk_text("a" * 100, 30)
        self.assertEqual([len(p) for p in parts], [30, 30, 30, 10])
        self.assertEqual("".join(parts), "a" * 100)

    def test_line_aware_split(self):
        text = "\n".join(f"line {i}: " + "x" * 50 for i in range(20))
        parts = _chunk_text(text, 200)
        # Each part <= 200 chars; no line broken in the middle
        for p in parts:
            self.assertLessEqual(len(p), 200)
        self.assertEqual("\n".join(parts).replace("\n\n", "\n"), text)

    def test_zero_max_len_returns_whole(self):
        self.assertEqual(_chunk_text("abc", 0), ["abc"])


class TestFeishuNotifierHttp(unittest.TestCase):
    """Token + send URLs are right, and a real send POSTs the right body."""

    def test_token_url_feishu(self):
        with mock.patch("hub.sync.feishu_notifier.urlopen") as u:
            u.return_value.__enter__.return_value.read.return_value = json.dumps(
                {"code": 0, "tenant_access_token": "t-abc", "expire": 7200}
            ).encode()
            n = FeishuNotifier(
                config={"app_id": "id", "app_secret": "secret", "domain": "feishu"}
            )
            self.assertEqual(n._get_token(), "t-abc")
            self.assertEqual(u.call_args.args[0].full_url, FEISHU_ENDPOINTS["feishu"]["auth"])
            u.reset_mock()
            # Second call hits the cache, no extra urlopen
            self.assertEqual(n._get_token(), "t-abc")
            u.assert_not_called()

    def test_token_url_lark(self):
        with mock.patch("hub.sync.feishu_notifier.urlopen") as u:
            u.return_value.__enter__.return_value.read.return_value = json.dumps(
                {"code": 0, "tenant_access_token": "t-lark", "expire": 7200}
            ).encode()
            n = FeishuNotifier(
                config={"app_id": "id", "app_secret": "secret", "domain": "lark"}
            )
            n._get_token()
            self.assertEqual(u.call_args.args[0].full_url, FEISHU_ENDPOINTS["lark"]["auth"])

    def test_token_error_returns_empty(self):
        with mock.patch("hub.sync.feishu_notifier.urlopen") as u:
            u.return_value.__enter__.return_value.read.return_value = json.dumps(
                {"code": 10003, "msg": "invalid param"}
            ).encode()
            n = FeishuNotifier(config={"app_id": "id", "app_secret": "secret"})
            self.assertEqual(n._get_token(), "")

    def test_send_message_url_and_body(self):
        with mock.patch("hub.sync.feishu_notifier.urlopen") as u:
            u.return_value.__enter__.return_value.read.return_value = json.dumps(
                {"code": 0, "data": {"message_id": "om_1"}}
            ).encode()
            n = FeishuNotifier(config={"app_id": "id", "app_secret": "secret"})
            # Pre-load token
            with mock.patch.object(n, "_get_token", return_value="t-1"):
                ok = n._post_message(
                    "oc_chat_1",
                    {"msg_type": "text", "content": json.dumps({"text": "hi"})},
                )
            self.assertTrue(ok)
            self.assertEqual(u.call_count, 1)
            req = u.call_args.args[0]
            self.assertIn("/open-apis/im/v1/messages", req.full_url)
            self.assertIn("receive_id_type=chat_id", req.full_url)
            self.assertEqual(req.headers["Authorization"], "Bearer t-1")
            body = json.loads(req.data.decode("utf-8"))
            self.assertEqual(body["receive_id"], "oc_chat_1")
            self.assertEqual(body["msg_type"], "text")

    def test_send_chunks_long_text(self):
        with mock.patch("hub.sync.feishu_notifier.urlopen") as u:
            u.return_value.__enter__.return_value.read.return_value = json.dumps(
                {"code": 0, "data": {"message_id": "om_1"}}
            ).encode()
            n = FeishuNotifier(
                config={
                    "app_id": "id",
                    "app_secret": "secret",
                    "max_message_length": 50,
                }
            )
            with mock.patch.object(n, "_get_token", return_value="t-1"):
                ok = n.send_text("x" * 137, receive_id="oc_chat")
            self.assertTrue(ok)
            # 137 / 50 -> 3 POSTs
            self.assertEqual(u.call_count, 3)


if __name__ == "__main__":
    unittest.main()
