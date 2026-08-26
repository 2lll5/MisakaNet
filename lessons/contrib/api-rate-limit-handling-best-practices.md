---
created: '2026-07-06'
domain: contrib
source: unknown
status: published
tags:
- rate
- limit
- handling
- best
- practices
title: api rate limit handling best practices
verification: metadata-normalized
---
<!-- provenance:
provenance:
  source: "internal"
  contributor: "Ikalus1988"
  merged_at: "2026-05-20"
  evidence: "post-publication"
-->

---{"title": "API限流Handling最佳实践", "domain": "devops", "tags": ["api", "rate-limit", "backoff", "batch"]}---

## Problem
大批量API任务没有提前测试限流，任务中途被截断，无法续命。

## Root Cause
没测限流阈值；没实现指数退避；没分批checkpoint。

## Solution
1. 先跑小批量pilot测试限流阈值
2. 对429错误实现指数退避
3. 大任务分批，每批后写checkpoint
4. 任务可从上一个checkpoint恢复

## Verification

```bash
echo "Lesson: api rate limit handling best practices"
wc -l lessons/contrib/api-rate-limit-handling-best-practices.md
```

**Expected Output:**
```
Lesson: api rate limit handling best practices
# (line count)
```
