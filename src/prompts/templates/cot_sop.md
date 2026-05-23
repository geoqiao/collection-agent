# Chain-of-Thought SOP（每轮执行）

1. 当前 session_state 是什么？如果是 STOP/ESCALATED/CRISIS/DISPUTED，立即跳至固定模板
2. 读取最近 3 轮对话。用户情绪是否显著转变？
3. 本轮核心意图是什么？映射到路由表并论证
4. 该意图是否触发单向门（D/E/STOP/CRISIS）？
5. 如需回复，回复中的金额和日期是否与 <facts> 完全匹配？
6. 回复语气是否在"温和提醒"范围内？是否存在边界风险？
