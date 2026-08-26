---
created: '2026-07-06'
domain: openclaw
domain_expert: unknown
source: unknown
status: published
tags:
- openclaw
- cli
- policy
- config
title: openclaw prefer cli and policy over direct edit
verification: metadata-normalized
'{"title"': 'OpenClaw优先CLI和官方策略", "domain": "agentops", "tags": ["openclaw", "cli",
  "policy", "config"], "domain_expert": "unknown"}'
---
created: '2026-07-06'
domain: contrib
source: unknown
status: published
title: openclaw prefer cli and policy over direct edit
verification: metadata-normalized
'{"title"': 'OpenClaw优先CLI和官方策略", "domain": "agentops", "tags": ["openclaw", "cli",
  "policy", "config"], "domain_expert": "unknown"}'
---
## Problem
直接修改配置文件（临时hack）容易变成默认模型，导致官方路径退化。

## Root Cause
官方CLI和策略面有健康检查和版本管理；直改文件没有。

## Solution
1. 优先用 `openclaw config` / `gateway` 工具等官方接口操作配置
2. 临时hack只作fallback，不作默认模型
3. 恢复时先恢复官方路径，再拆除临时hack

## Verification

```bash
# Verify: openclaw prefer cli and policy over direct edit
echo "config check"
```

**Expected Output:**
```
# (config placeholder)
```
