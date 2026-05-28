---
name: stop
description: 用户明确要求停止联系时使用。确认退出，加入DNC名单，停止所有触达。
tools: [add_to_dnc, pause_collection]
max_steps: 2
---

# STOP 处理 Skill

## 目标
尊重用户意愿，立即停止所有联系，加入免打扰名单。

## 执行流程
1. **调用 `add_to_dnc`**，加入免打扰名单
2. 礼貌确认已停止联系
3. 告知如有需要可主动联系客服

## 约束
- ❌ 禁止劝说用户继续
- ❌ 禁止辩解
- ✅ 语气礼貌、尊重
- ✅ 确认后立即终止
