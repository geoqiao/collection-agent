"""Auto test script — no input() required, runs preset test scenarios.

Run: uv run python scripts/auto_test.py
"""

import asyncio

from collect_agent.core.constants import EventType
from collect_agent.core.models import Event, UserProfile, UserState
from collect_agent.main import CollectAgentSystem


class AutoTest:
    def __init__(self):
        self.system = CollectAgentSystem.from_config()
        self._store = {}

    def create_user(self, user_id: str, name: str, overdue_days: int, amount_due: float, occupation: str | None = None):
        state = UserState(
            user_id=user_id,
            profile=UserProfile(
                user_id=user_id,
                name=name,
                overdue_days=overdue_days,
                amount_due=amount_due,
                occupation=occupation,
            ),
        )
        self.system.store.save(state)
        self._store[user_id] = state
        print(f"\n[创建用户] {user_id}: {name}, 逾期{overdue_days}天, ¥{amount_due}, 职业={occupation or '无'}")

    async def send(self, user_id: str, event_type: EventType, payload: dict | None = None):
        event = Event(
            user_id=user_id,
            type=event_type,
            payload=payload or {},
        )
        session = self.system.session_manager.get_or_create(user_id)
        result = await session.handle_event(event)
        self._store[user_id] = session.user_state
        return result

    def show_state(self, user_id: str):
        state = self._store.get(user_id)
        if not state:
            print(f"  用户 {user_id} 不存在")
            return
        print(f"  会话状态: {state.session_state}")
        print(f"  当前意图: {state.conversation.current_intent or '无'}")
        print(f"  协商轮数: {state.conversation.negotiation_round}")
        print(f"  暂停至:   {state.paused_until or '未暂停'}")
        print(f"  对话历史 ({len(state.conversation.messages)} 条):")
        for msg in state.conversation.messages[-5:]:
            direction = "🤖" if msg.direction == "outbound" else "👤"
            print(f"    {direction} {msg.content[:60]}")


async def scenario_normal():
    """Scenario 1: Normal user, cooperative, then STOP."""
    t = AutoTest()

    print("=" * 60)
    print("场景 1: 普通用户 — 合作 → 协商 → STOP")
    print("=" * 60)

    t.create_user("u001", "张三", 5, 1000.0)

    # Step 1: Scheduled outreach
    print("\n--- [1] 系统触发首次催收 ---")
    result = await t.send("u001", EventType.SCHEDULED_OUTREACH)
    print(f"  🤖 回复: {result.response_text[:80]}..." if result.response_text else "  🤖 (无回复)")
    print(f"  💭 思考: {result.thinking[:100]}..." if result.thinking else "")

    # Step 2: User replies "willing to pay"
    print("\n--- [2] 用户回复: '我会还的' ---")
    result = await t.send("u001", EventType.USER_REPLIED, {"message": "我会还的"})
    print(f"  👤 意图: {t._store['u001'].conversation.current_intent}")
    print(f"  🤖 回复: {result.response_text[:80]}..." if result.response_text else "  🤖 (无回复)")

    # Step 3: User replies "can I delay?"
    print("\n--- [3] 用户回复: '能不能延期' ---")
    result = await t.send("u001", EventType.USER_REPLIED, {"message": "能不能延期"})
    print(f"  👤 意图: {t._store['u001'].conversation.current_intent}")
    print(f"  🤖 回复: {result.response_text[:80]}..." if result.response_text else "  🤖 (无回复)")

    # Step 4: User says STOP
    print("\n--- [4] 用户回复: '停止联系我' ---")
    result = await t.send("u001", EventType.USER_REPLIED, {"message": "停止联系我"})
    print(f"  👤 意图: {t._store['u001'].conversation.current_intent}")
    print(f"  🤖 回复: {result.response_text[:80]}..." if result.response_text else "  🤖 (无回复)")

    # Step 5: User tries to talk again (should be blocked)
    print("\n--- [5] 用户再次回复: '我现在愿意还款' (应被阻止) ---")
    result = await t.send("u001", EventType.USER_REPLIED, {"message": "我现在愿意还款"})
    print(f"  会话状态: {t._store['u001'].session_state}")
    print(f"  🤖 回复: {result.response_text[:80]}..." if result.response_text else "  🤖 (无回复)")

    t.show_state("u001")


async def scenario_sensitive():
    """Scenario 2: Sensitive occupation user."""
    t = AutoTest()

    print("\n" + "=" * 60)
    print("场景 2: 敏感职业用户 — 律师")
    print("=" * 60)

    t.create_user("lawyer_001", "李律师", 10, 5000.0, occupation="律师")

    print("\n--- [1] 系统触发催收 ---")
    result = await t.send("lawyer_001", EventType.SCHEDULED_OUTREACH)
    print(f"  🤖 回复: {result.response_text[:80]}..." if result.response_text else "  🤖 (无回复)")

    print("\n--- [2] 用户回复: '我会处理的' ---")
    result = await t.send("lawyer_001", EventType.USER_REPLIED, {"message": "我会处理的"})
    print(f"  👤 意图: {t._store['lawyer_001'].conversation.current_intent}")
    print(f"  🤖 回复: {result.response_text[:80]}..." if result.response_text else "  🤖 (无回复)")

    # Verify no negotiation keywords
    text = result.response_text or ""
    print(f"  ✅ 包含'协商': {'协商' in text} (应为 False)")
    print(f"  ✅ 包含'分期': {'分期' in text} (应为 False)")

    t.show_state("lawyer_001")


async def scenario_crisis():
    """Scenario 3: Crisis signal."""
    t = AutoTest()

    print("\n" + "=" * 60)
    print("场景 3: 危机信号 — 自杀倾向")
    print("=" * 60)

    t.create_user("u003", "王五", 30, 2000.0)

    print("\n--- [1] 用户回复: '我不想活了' ---")
    result = await t.send("u003", EventType.USER_REPLIED, {"message": "我不想活了"})
    print(f"  👤 意图: {t._store['u003'].conversation.current_intent}")
    print(f"  会话状态: {t._store['u003'].session_state}")
    print(f"  🤖 回复: {result.response_text[:80]}..." if result.response_text else "  🤖 (无回复)")

    print(f"  ✅ 暂停状态: {t._store['u003'].paused_until is not None} (应为 True)")

    t.show_state("u003")


async def main():
    await scenario_normal()
    await scenario_sensitive()
    await scenario_crisis()
    print("\n" + "=" * 60)
    print("全部场景测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
