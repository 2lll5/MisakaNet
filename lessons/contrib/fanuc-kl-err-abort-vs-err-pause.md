---
confidence: '0.7'
created: '2026-05-03'
domain: fanuc
domain_expert: bootstrap
language: zh
source: bootstrap
status: published
subdomain: error-handling
tags:
- fanuc
- abort
- pause
title: 'FANUC KL: ERR_ABORT vs ERR_PAUSE 行为差异'
verified_date: '2026-05-03'
---
## FANUC KL: ERR_ABORT vs ERR_PAUSE 行为差异

### Problem描述
IPC 通信错误时未区分 ERR_ABORT 和 ERR_PAUSE，导致程序号丢失。

### Root Cause
- ERR_ABORT=2：所有任务中止（导致丢程序号）
- ERR_PAUSE=1：仅暂停当前任务，不影响其他任务

### Solution方法
IPC 超时类错误应使用 ERR_PAUSE 而非 ERR_ABORT，避免级联中止。

### Verification方式
模拟 IPC 超时，确认程序号在 ERR_PAUSE 场景下保留。


## Verification

```bash
# Verify: FANUC KL: ERR_ABORT vs ERR_PAUSE 行为差异
grep -r "fanuc" lessons/contrib/fanuc-*.md 2>/dev/null | wc -l
```

**Expected Output:**
```
# (FANUC lesson count)
```
