---
name: negotiation
description: 与债务人协商还款计划或延期
tools: [query_bill, pause_collection, record_promise, schedule_reminder]
max_steps: 3
---

# 协商 Skill

## 目标
在用户经济困难时，通过协商获得还款承诺，避免直接对抗。

## 执行流程
1. 表达理解用户困难
2. 查询账单事实（从 facts 读取）
3. 提供可行的还款方案（分期 / 延期）
4. 记录用户承诺
5. 安排后续提醒

## 约束
- ❌ 不得承诺减免金额（需人工审批）
- ❌ 不得施加不当压力
- ✅ 语气共情、理解
- ✅ 所有金额必须从 facts 读取
