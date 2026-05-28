---
name: payment_guidance
description: 引导用户完成还款操作
tools: [query_bill, send_payment_link]
max_steps: 3
---

# 还款引导 Skill

## 目标
协助用户完成还款操作。

## 执行流程
1. 确认账单金额（从 facts 读取）
2. 提供还款方式
3. 发送支付链接
4. 确认还款结果

## 约束
- ✅ 步骤清晰、简洁
- ✅ 所有金额必须从 facts 读取
