---
confidence: 0.9
created: 2026-05-03
domain: fanuc
id: fanuc-kl-bytes-ahead-is-builtin-procedure
language: zh
problem: KL 编译报错时，误认为 BYTES_AHEAD 是禁用标识符或非法调用，将其从 MM_RCV_NTFY.kl 中删除。
quality_score: 80
root_cause: BYTES_AHEAD 是 Karel 语言的内置系统调用（Built-in Procedure），用法完全正确。KL 语言保留字（禁用标识符）有特定列表，BYTES_AHEAD
  不在其中。
solution: 恢复 MM_RCV_NTFY.kl 中所有 BYTES_AHEAD 调用，不应删除。禁用标识符列表：SECONDS、ENDDO、ELSEIF 等（详见
  fanuc-kl-compile SKILL.md）。
source: 实操经验
status: published
subdomain: kl-syntax
tags:
- fanuc
- karel
- ktrans
- reserved-words
- built-in
title: 'FANUC KL: BYTES_AHEAD 是 Karel 内置 Procedure'
updated: 2026-07-06
verification: KTRANS 编译 MM_RCV_NTFY.kl，无 BYTES_AHEAD 相关报错。
---
## FANUC KL: BYTES_AHEAD 是 Karel 内置 Procedure

### Problem描述
KL 编译报错时，误认为 BYTES_AHEAD 是禁用标识符或非法调用，将其从 MM_RCV_NTFY.kl 中删除。

### Root Cause
BYTES_AHEAD 是 Karel 语言的内置系统调用（Built-in Procedure），用法完全正确。KL 语言保留字（禁用标识符）有特定列表，BYTES_AHEAD 不在其中。

### Solution方法
恢复 MM_RCV_NTFY.kl 中所有 BYTES_AHEAD 调用，不应删除。禁用标识符列表：SECONDS、ENDDO、ELSEIF 等（详见 fanuc-kl-compile SKILL.md）。

### Verification方式
KTRANS 编译 MM_RCV_NTFY.kl，无 BYTES_AHEAD 相关报错。


## Verification

```bash
# Verify: FANUC KL: BYTES_AHEAD 是 Karel 内置 Procedure
grep -r "fanuc" lessons/contrib/fanuc-*.md 2>/dev/null | wc -l
```

**Expected Output:**
```
# (FANUC lesson count)
```
