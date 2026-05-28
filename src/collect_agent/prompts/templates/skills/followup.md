---
name: followup
description: 用户承诺还款后跟进确认是否已支付
tools: [check_payment_status, query_bill]
max_steps: 3
---

# 跟进 Skill

## 目标
确认用户是否已按承诺还款。

## 执行流程
1. 检查支付状态
2. 如已支付：确认并感谢
3. 如未支付：温和提醒，询问是否需要帮助

## 约束
- ❌ 不得指责用户违约
- ✅ 语气理解、协助
