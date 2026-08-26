---
created: '2026-07-06'
domain: feishu
source: unknown
status: published
tags:
- feishu
- block
- batch
- limit
title: feishu block batch limit
verification: metadata-normalized
---
## 飞书 Block 批量写入上限

## Problem
调用飞书文档 `document.blocks.children.create` API 批量创建 block 时，每次请求超过约 20 个 block 会触发限流（HTTP 429）或发生静默截断（请求成功但部分 block 未写入）。

## Root Cause
飞书服务端对 `document.blocks.children.create` 单次请求的 `children` 数组长度存在隐性上限（实测约为 20），该限制未在官方文档中明确说明。超出上限时，服务端行为不一致：有时返回限流错误，有时静默丢弃超出部分。

## Solution
- 每批请求的 block 数量控制在 **≤ 20 个**。
- 超量时将 block 列表分批，每批之间加入 **500ms 延迟**（经验值，用于规避连续请求触发限流）。
- 示例分批逻辑：

```python
import time

def batch_create_blocks(client, doc_id, blocks, batch_size=20, interval=0.5):
    for i in range(0, len(blocks), batch_size):
        batch = blocks[i:i + batch_size]
        client.document.blocks.children.create(doc_id, children=batch)
        if i + batch_size < len(blocks):
            time.sleep(interval)
```

## Verification

```bash
# 验证：创建超过 20 个 block 时是否触发截断或限流
# 预期：≤20 个时全部写入成功；>20 个时出现截断或 429 错误
python test_feishu_batch.py --count 25 --doc-id <DOC_ID>
```

**Expected Output:**
```
# blocks_requested=25, blocks_created=20 (截断) 或 HTTP 429 (限流)
```
