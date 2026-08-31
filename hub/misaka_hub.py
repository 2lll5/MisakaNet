"""
MisakaHub — 轻量同步调度器 + 知识图谱 + 仲裁管理

不再是"中心协调节点"，而是可选的"图书馆管理员":
- 定时 git pull/push 同步
- 知识图谱构建
- 冲突时创建 GitHub Issue（取代飞书卡片）
- 可选通知通道（Discord/Slack/Email）
"""
import asyncio
import json
import yaml
import os
import re
from pathlib import Path

# Storage
from hub.storage.knowledge_graph import KnowledgeGraph

# Orchestrator
from hub.orchestrator.skill_indexer import SkillIndexer

# Sync
from hub.sync.sync_scheduler import SyncScheduler

# Notifiers
from hub.sync.notifier import DiscordNotifier, SlackNotifier, EmailNotifier
from hub.sync.feishu_notifier import FeishuNotifier

# Master
from hub.master.token_manager import TokenManager, AuditLogger


class MisakaHub:
    """
    轻量 Hub — 只做三件事：
    1. 定时同步各节点知识
    2. 检测知识冲突，创建 GitHub Issue
    3. 可选通知（Discord/Slack/Email）
    """

    def __init__(self, config_path: str = "./hub/config.yaml"):
        self.config = self._load_config(config_path)

        # 知识图谱
        kg_config = self.config["storage"]["graph"]
        kg_path = kg_config.get("persist_path", "./hub/storage/knowledge_graph/graph.gpickle")
        self.knowledge_graph = KnowledgeGraph(persist_path=kg_path)

        # 技能索引
        self.skill_indexer = SkillIndexer(graph_path=kg_path)

        # 同步调度器（核心功能）
        sync_config = self.config.get("sync", {})
        self.sync_scheduler = SyncScheduler(
            interval_minutes=sync_config.get("interval_minutes", 30)
        )

        # 通知通道（可选配置）
        self.notifiers = []
        notifier_config = self.config.get("notifier", {})
        for channel, cls in [("discord", DiscordNotifier), ("slack", SlackNotifier)]:
            url = notifier_config.get(channel, {}).get("webhook_url", "")
            if url:
                self.notifiers.append(cls(url))

        # Feishu — reuse Hermes Agent's bot credentials if present.
        # Hermes reads FEISHU_APP_ID/SECRET/HOME_CHANNEL from ~/.hermes/.env
        # (see ~/.hermes/hermes-agent/gateway/run.py). When operators
        # `source` that env before launching the hub, we get the same bot
        # pushing into the same chat the operator already uses.
        feishu_config = notifier_config.get("feishu", {})
        feishu_enabled = (
            feishu_config.get("enabled", False)
            or bool(os.environ.get("FEISHU_APP_ID"))
        )
        if feishu_enabled:
            self.notifiers.append(FeishuNotifier(config=feishu_config))

        if os.environ.get("EMAIL_SMTP_HOST"):
            self.notifiers.append(EmailNotifier())

        channel_names = [c.__class__.__name__ for c in self.notifiers]
        print(f"  🔔 通知通道: {' + '.join(channel_names) if channel_names else '未配置'}")

        self.sync_scheduler.add_callback(self._on_sync_cycle)

    def _load_config(self, config_path: str) -> dict:
        with open(config_path, 'r') as f:
            raw = f.read()

        def _replace_env(match):
            var = match.group(1)
            return os.environ.get(var, "")
        raw = re.sub(r'\$\{([^}]+)\}', _replace_env, raw)
        return yaml.safe_load(raw)

    async def _on_sync_cycle(self, sync_version: int):
        print(f"[Hub] Sync cycle {sync_version} triggered")
        self._rebuild_skill_index()

        skill_count = len(self.knowledge_graph.get_all_skills())
        self._notify_all("notify_sync_ready", agent_id="hub", skill_count=skill_count)

    def _rebuild_skill_index(self):
        skills = self.knowledge_graph.get_all_skills()
        for skill in skills:
            self.skill_indexer.register_skill(skill)

    def _notify_all(self, method: str, *args, **kwargs):
        for n in self.notifiers:
            try:
                getattr(n, method)(*args, **kwargs)
            except Exception as e:
                print(f"  ⚠️ 通知失败 ({n.__class__.__name__}): {e}")

    # ── 生命周期 ──

    async def start(self):
        print(f"\n{'='*40}")
        print(f"  MisakaHub 启动")
        print(f"{'='*40}")
        self.sync_scheduler.start()
        print(f"[Hub] 就绪 (同步间隔: {self.sync_scheduler.interval_minutes} 分钟)")
        print()

    async def stop(self):
        self.sync_scheduler.stop()
        print("[Hub] 已停止")

    def status(self) -> dict:
        skill_count = len(self.knowledge_graph.get_all_skills())
        return {
            "hub_name": self.config.get("hub", {}).get("name", "misaka-hub"),
            "version": self.config.get("hub", {}).get("protocol_version", "1.0"),
            "skills": skill_count,
            "notifiers": [n.__class__.__name__ for n in self.notifiers],
        }


async def main():
    hub = MisakaHub(config_path="./config.yaml")
    try:
        await hub.start()
        while True:
            await asyncio.sleep(3600)
            print(f"[Hub] 状态: {hub.status()}")
    except KeyboardInterrupt:
        await hub.stop()


if __name__ == "__main__":
    asyncio.run(main())
