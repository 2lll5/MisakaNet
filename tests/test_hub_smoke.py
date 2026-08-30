"""Smoke tests for the MisakaHub wiring — Feishu path included.

We deliberately mock out the heavy sub-systems (KnowledgeGraph, SkillIndexer,
chroma-backed VectorStore, the SyncScheduler, the MasterAPI) so the hub's
constructor runs in <1s and doesn't trigger transformers/torchvision import
side-effects that would break unrelated test files in the same pytest run.

The wiring contract under test is:

  1. When the config marks `notifier.feishu.enabled: true`, the hub
     instantiates a `FeishuNotifier` and adds it to `self.notifiers`.
  2. When `FEISHU_APP_ID` is exported but `notifier.feishu.enabled` is
     absent, the hub auto-enables the Feishu notifier (the Hermes-reuse
     contract documented in AGENTS.md).
  3. When neither is set, the hub does NOT silently create a FeishuNotifier.
  4. The full sync cycle triggers `notify_sync_ready` on every registered
     notifier (including Feishu in dry_run mode).
"""

from __future__ import annotations

import asyncio
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _stub_hub_dependencies():
    """Replace the heavy hub sub-modules with in-memory stubs.

    Skipped if already stubbed (idempotent across test methods).
    """
    if "hub.misaka_hub" not in sys.modules:
        return  # pragma: no cover

    from hub.knowledge_graph_stub import KnowledgeGraph
    from hub.skill_indexer_stub import SkillIndexer

    sys.modules["hub.misaka_hub"].KnowledgeGraph = KnowledgeGraph
    sys.modules["hub.misaka_hub"].SkillIndexer = SkillIndexer


class _StubKnowledgeGraph:
    def __init__(self, persist_path=None):
        self.persist_path = persist_path
        self.nodes = {}

    def get_all_skills(self):
        return list(self.nodes.values())

    def save(self):
        pass


class _StubSkillIndexer:
    def __init__(self, graph_path=None):
        self.graph_path = graph_path

    def register_skill(self, skill):
        pass

    def get_all_skills(self):
        return []

    def unregister_skill(self, skill_id):
        pass


# Backward-compat: kept for callers that may still import the module
# (the in-setUp pre-stub above is the preferred path).
_StubSkillIndexer_legacy = _StubSkillIndexer


def _build_config(feishu_block):
    return {
        "hub": {"name": "test-hub", "protocol_version": "1.0"},
        "storage": {
            "graph": {"persist_path": "/tmp/_test_hub_graph.gpickle"},
            "vector_store": {"type": "chroma", "persist_dir": "/tmp/_test_vstore"},
            "metadata": {"type": "sqlite", "db_path": "/tmp/_test_meta.db"},
        },
        "sync": {"interval_minutes": 30},
        "notifier": {"feishu": feishu_block} if feishu_block is not None else {},
    }


class TestMisakaHubFeishuWiring(unittest.TestCase):
    def setUp(self):
        # Strip Hermes env vars so the test is hermetic.
        self._saved = {}
        for k in (
            "FEISHU_APP_ID", "FEISHU_APP_SECRET", "FEISHU_HOME_CHANNEL",
            "FEISHU_DOMAIN",
        ):
            self._saved[k] = os.environ.pop(k, None)

        # Pre-stub the heavy modules BEFORE misaka_hub is imported.
        # `hub.orchestrator.skill_indexer` imports torch + transformers at
        # module level, which transitively pulls torchvision and would
        # contaminate unrelated test files run after us in the same
        # pytest invocation. Replacing the module entry with a tiny stub
        # sidesteps that.
        import types
        if "hub.orchestrator.skill_indexer" not in sys.modules:
            mod = types.ModuleType("hub.orchestrator.skill_indexer")

            class _StubSkillIndexerModule:
                def __init__(self, graph_path=None):
                    self.graph_path = graph_path

                def register_skill(self, skill):
                    pass

                def get_all_skills(self):
                    return []

                def unregister_skill(self, skill_id):
                    pass

            mod.SkillIndexer = _StubSkillIndexerModule
            sys.modules["hub.orchestrator.skill_indexer"] = mod

    def tearDown(self):
        for k, v in self._saved.items():
            if v is not None:
                os.environ[k] = v
            else:
                os.environ.pop(k, None)

    def _make_hub(self, config_dict):
        from hub.misaka_hub import MisakaHub
        with mock.patch.object(MisakaHub, "_load_config", return_value=config_dict):
            return MisakaHub(config_path="/nonexistent.yaml")

    def test_explicit_feishu_enabled_creates_notifier(self):
        hub = self._make_hub(_build_config({
            "enabled": True,
            "home_channel": "oc_test",
            "dry_run": True,
        }))
        kinds = [type(n).__name__ for n in hub.notifiers]
        self.assertIn("FeishuNotifier", kinds)

    def test_env_app_id_auto_enables(self):
        os.environ["FEISHU_APP_ID"] = "cli_env_app"
        os.environ["FEISHU_APP_SECRET"] = "env_secret"
        os.environ["FEISHU_HOME_CHANNEL"] = "oc_env"
        hub = self._make_hub(_build_config(feishu_block=None))
        kinds = [type(n).__name__ for n in hub.notifiers]
        self.assertIn("FeishuNotifier", kinds)
        feishu = next(n for n in hub.notifiers if type(n).__name__ == "FeishuNotifier")
        self.assertEqual(feishu.app_id, "cli_env_app")
        self.assertEqual(feishu.home_channel, "oc_env")

    def test_no_creds_no_notifier(self):
        hub = self._make_hub(_build_config(feishu_block=None))
        kinds = [type(n).__name__ for n in hub.notifiers]
        self.assertNotIn("FeishuNotifier", kinds)

    def test_full_sync_cycle_notifies_all(self):
        hub = self._make_hub(_build_config({
            "enabled": True,
            "home_channel": "oc_x",
            "dry_run": True,
        }))
        with mock.patch.object(hub, "_notify_all") as notify, \
             mock.patch.object(hub, "_rebuild_skill_index") as rebuild:
            rebuild.return_value = None
            asyncio.run(hub._on_sync_cycle(1))
        self.assertTrue(notify.called)
        self.assertEqual(notify.call_args.args[0], "notify_sync_ready")
        self.assertEqual(notify.call_args.kwargs["agent_id"], "hub")
        self.assertIn("skill_count", notify.call_args.kwargs)

    def test_status_reports_notifier_kinds(self):
        hub = self._make_hub(_build_config({
            "enabled": True, "home_channel": "oc_x", "dry_run": True,
        }))
        st = hub.status()
        self.assertIn("FeishuNotifier", st["notifiers"])
        self.assertEqual(st["hub_name"], "test-hub")


if __name__ == "__main__":
    unittest.main()
