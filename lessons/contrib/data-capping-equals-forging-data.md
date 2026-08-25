---
title: "数据封顶=伪造数据：超出阈值应剔除而非截断"
domain: "data"
subdomain: "data-quality"
tags:
  - data-quality
  - threshold
  - capping
  - data-integrity
source: "<user>"
status: "published"
confidence: "1.0"
created: "2026-06-25"
domain_expert: "<user>"
verified_date: "2026-07-06"
---

## Problem

数据分析中，当数据超出阈值（如实际节拍超过工位节拍），把超出部分"封顶"到阈值值（如写成 100%），本质上是伪造满负荷数据。后续计算基于伪造数据得出错误结论。

## Root Cause

封顶和剔除是两种完全不同的操作：
- **封顶** = 把异常值截断到阈值 → 掩盖真实异常，污染后续计算
- **剔除** = 承认数据异常并排除 → 保持数据诚实

"Z>P 封顶 100%"是典型的封顶陷阱：超出阈值的数据被强制拉回阈值，看起来"合理"但完全失真。

## Solution

1. **超出阈值的数据直接剔除**（保持空值），不参与后续计算
2. 任何口径都不能"封顶"异常数据
3. 剔除后需记录剔除数量和比例，供审计追溯
4. 如果阈值本身不合理，应调整阈值而非封顶数据

```python
# ❌ 封顶 = 伪造
utilization = min(actual_cycle / target_cycle, 1.0)

# ✅ 剔除 = 诚实
if actual_cycle > target_cycle:
    utilization = None  # 标记为异常，不参与统计
else:
    utilization = actual_cycle / target_cycle
```

## Verification

```bash
echo "Lesson: 数据封顶=伪造数据：超出阈值应剔除而非截断"
wc -l lessons/contrib/data-capping-equals-forging-data.md
```

**Expected Output:**
```
Lesson: 数据封顶=伪造数据：超出阈值应剔除而非截断
# (line count)
```
