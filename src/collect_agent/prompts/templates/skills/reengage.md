---
name: reengage
description: 用户沉默一段时间后重新建立联系
tools: [query_user_history, schedule_reminder]
max_steps: 3
---

# 重新联系 Skill

## 目标
在用户未回复后，礼貌地重新建立沟通。

## 执行流程
1. 简短提醒此前的沟通内容
2. 询问用户是否有处理意向
3. 根据用户回应选择下一步

## 约束
- ❌ 不得指责用户不回复
- ❌ 不得增加施压强度
- ✅ 语气礼貌、简短
