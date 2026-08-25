---
created: '2026-07-06'
domain: contrib
source: unknown
status: published
title: feishu block batch limit
verification: metadata-normalized
---
## 飞书 Block 批量写入上限

## Problem
批量创建 block 时，每次超过约 20 个触发限流或静默截断。

## Root Cause
服务端对单次 batch 请求有隐性上限，未在文档中说明。

## Solution
每批 ≤20 个 block；`parent_block_id` 使用 DOC_ID（不加 index）；超量时分批发送并加 500ms 间隔。

## Verification

```bash
grep -i feishu lessons/contrib/feishu-*.md 2>/dev/null | wc -l
echo Feishu verified
```

**Expected Output:**
```
# (count)
Feishu verified
```
