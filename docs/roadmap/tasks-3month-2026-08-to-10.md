# MisakaNet 3-Month Task Breakdown (Aug-Oct 2026)

> 主战略：AI agent 的 redacted failure-memory + intake + reuse layer

---

## 8月 — v2.13 收尾 + v2.14 核心

### Intake flywheel（收尾）

| # | 任务 | 优先级 | 交付物 | 状态 |
|---|---|---|---|---|
| 1 | --feedback flag 接入 intake 通道 | P1 | search_knowledge.py --feedback 写入 contribution_queue | ⏳ #622 DCO |
| 2 | demand board 接入 Worker KV | P1 | register-proxy-sw.js demand-board endpoint | ❌ |
| 3 | intake digest 脚本 | P2 | scripts/intake_digest.py 读取 KV 导出并分类统计 | ❌ |

### Trust & curation（v2.14 核心）

| # | 任务 | 优先级 | 交付物 | 状态 |
|---|---|---|---|---|
| 4 | review queue 状态机 | P0 | contribution_queue.py 已实现，需接入 Worker | ✅ #649 |
| 5 | trust semantics 统一 | P0 | README/docs/site 统一 indexed/published/verified | ❌ |
| 6 | regression queries fixtures | P1 | data/regression_queries.json 补充到 20+ 条 | ❌ |
| 7 | duplicate governance 决策规则 | P1 | docs/duplicate-policy.md | ❌ |
| 8 | contribution quality scorer 集成 | P1 | 提交时自动跑 quality_scorer.py | ❌ |

### Distribution（持续）

| # | 任务 | 优先级 | 交付物 | 状态 |
|---|---|---|---|---|
| 9 | MCP Registry 发布 | P1 | 等网络通时手动 mcp-publisher publish | ⏸️ |
| 10 | llms.txt 更新 | P2 | 反映 4 个 MCP tools + intake 能力 | ❌ |

---

## 9月 — Runtime entry + i18n

### Runtime entry（新支线）

| # | 任务 | 优先级 | 交付物 |
|---|---|---|---|
| 11 | Cursor wrapper 设计 | P0 | .cursorrules 增强：失败时自动建议 search MisakaNet |
| 12 | Claude Code hook 设计 | P0 | 失败场景下触发 misakanet_search 的 hook/wrapper |
| 13 | runtime middleware prototype | P1 | scripts/misaka_middleware.py — 捕获异常 → search → 返回建议 |
| 14 | entry point 测试 | P1 | 至少 2 个真实失败场景验证 middleware 有效 |

**关键约束：** 先做"失败后建议"，不做"无感自愈中枢"。不自动重试，不自动修复。

### i18n（增长）

| # | 任务 | 优先级 | 交付物 |
|---|---|---|---|
| 15 | 韩语 lesson 入库 | P1 | 至少 1 篇高质量韩语 lesson（#651） |
| 16 | 日语 lesson 入库 | P1 | 至少 1 篇高质量日语 lesson（#652） |
| 17 | 语言元数据支持 | P2 | search_knowledge.py --lang 支持语言过滤 |

### Trust（收尾）

| # | 任务 | 优先级 | 交付物 |
|---|---|---|---|
| 18 | lesson trust badge | P2 | 每篇 lesson 显示 indexed/published/verified 状态 |
| 19 | quality scorer 阈值校准 | P2 | 验证 75 分阈值是否合理（过高漏好 lesson，过低放垃圾） |

---

## 10月 — v2.15 readiness + benchmark

### Distribution confidence（v2.15）

| # | 任务 | 优先级 | 交付物 |
|---|---|---|---|
| 20 | MCP runtime verification | P0 | 部署后 tools/list 验证所有 tool 可用 |
| 21 | server.json 元数据刷新 | P1 | description + version + counts 对齐 |
| 22 | Glama 质量跟进 | P1 | score 页面更新，不破坏安装路径 |
| 23 | GitHub /mcp 候选 | P2 | 条件：Registry 活跃 + Glama 评估通过 + 元数据干净 |

### Benchmark（品牌）

| # | 任务 | 优先级 | 交付物 |
|---|---|---|---|
| 24 | bench-core 内部化 | P2 | benchmark 作为内部验证工具，不绑主仓库 |
| 25 | 有/无 MisakaNet 修复率对比 | P2 | 数据：修复率差多少、复用率提升多少 |

### Tiered access（如果 ready）

| # | 任务 | 优先级 | 交付物 |
|---|---|---|---|
| 26 | Remote MCP auth 原型 | P2 | /api/mcp/* 端点 + token 验证 |
| 27 | usage_status 端点 | P2 | 远程 quota 查询 |
| 28 | private lesson tier 评估 | P3 | 决定哪些 lesson 进 private，不动代码 |

---

## 里程碑总览

| 月 | 版本 | 核心闭环 | 验收标准 |
|---|---|---|---|
| 8月 | v2.14 | intake → review → trust | intake cluster → maintainer review → trusted artifact |
| 9月 | v2.14.1 | runtime entry + i18n | 至少 1 个 entry point 在真实失败场景下返回有用建议 |
| 10月 | v2.15 | distribution confidence | MCP runtime 验证通过 + 元数据一致 + Glama 评估 |

---

## 不做的事（3个月内）

- ❌ 通用 Agent 框架 / 多编排器兼容
- ❌ 自动重试闭环默认开启
- ❌ 拆掉 fatal-guard
- ❌ VS Code extension 单独切出去
- ❌ benchmark 作为第一战略
- ❌ "全栈防御体系"叙事
- ❌ Smithery 恢复
- ❌ GitHub /mcp 强推
