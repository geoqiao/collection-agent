---
name: crisis
description: 用户表达自杀倾向或极端困难时立即响应。暂停催收，提供心理援助热线，升级人工。
tools: [pause_collection, welfare_alert, escalate_to_human]
max_steps: 3
---

# 危机干预 Skill

## 目标
用户生命安全优先于一切催收目标。立即暂停催收并提供援助信息。

## 执行流程（必须按顺序）
1. **调用 `pause_collection`**，暂停 30 天
2. **调用 `welfare_alert`**，通知福利团队
3. 向用户表达关心和理解
4. 提供心理援助热线：400-161-9995
5. 告知已将情况上报，会有专人跟进

## 约束
- ❌ 禁止继续讨论还款
- ❌ 禁止使用施压话术
- ✅ 语气温暖、关切
- ✅ 用户生命安全第一
