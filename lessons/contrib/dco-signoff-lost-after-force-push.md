---
created: '2026-08-18'
domain: devops
domain_expert: ''
evidence_level: E2
language: zh
provenance:
  contributor: 2lll5
  evidence: pr-merged
  merged_at: '2026-07-20'
  original_issue: '#298'
  source: agent-debugging
source: mcp-intake-1099
status: published
tags:
- dco
- git
- force-push
- signoff
- ci
title: DCO signoff 在 force push 后丢失导致 PR DCO 检查失败
updated: ''
verified_date: ''
---
## Problem

DCO signoff 在 force push 后丢失，即使本地 commit 有 Signed-off-by，PR DCO 检查仍失败。

## Root Cause

GitHub Actions 的 DCO 检查会检查 PR 中所有 commit，不只是最新的。如果 force push 重写了 commit 历史，原始的 Signed-off-by 可能丢失。

常见原因：
1. `git rebase -i` 后没有 `--signoff`
2. `git commit --amend` 后 force push 丢失了其他 commit 的 signoff
3. 合并分支时没有保留 signoff

## Solution

**确保所有 commit 都有 signoff：**

```bash
# 方法1：rebase 时自动 signoff
git rebase --signoff HEAD~N

# 方法2：amend 当前 commit
git commit --amend --signoff --no-edit

# 方法3：检查所有 commit 是否有 signoff
git log --format="%H %s" | while read hash msg; do
  if ! git log -1 --format="%B" $hash | grep -q "Signed-off-by:"; then
    echo "Missing signoff: $hash $msg"
  fi
done
```

**预防措施：**
- 在 `.gitconfig` 中设置 `git config format.signoff true`
- 使用 `git commit -s` 而不是 `git commit`
- CI 中添加 DCO 检查 pre-commit hook

## Verification

```bash
# Verify: DCO signoff 在 force push 后丢失导致 PR DCO 检查失败
git rebase --signoff HEAD~N
```

**Expected Output:**
```
# (command should succeed without errors)
```

## Key Points

- DCO 检查检查所有 commit，不只是最新的
- force push 可能丢失 signoff
- 使用 `git rebase --signoff` 确保 rebase 后保留 signoff
