"""Interactive test client for Collect Agent.

Run: uv run python scripts/test_client.py
"""

# ruff: noqa: ASYNC250

import asyncio
import sys

from collect_agent.core.constants import EventType
from collect_agent.core.models import Event, UserProfile, UserState
from collect_agent.main import CollectAgentSystem
from collect_agent.skills.base import SkillResult


def safe_input(prompt: str = "") -> str:
    """Read line from stdin with explicit UTF-8 decoding.

    Works around encoding issues when running under uv / subprocess.
    """
    if prompt:
        print(prompt, end="", flush=True)
    try:
        raw = sys.stdin.buffer.readline()
        return raw.decode("utf-8", errors="replace").strip()
    except Exception:
        return ""


class TestClient:
    """Interactive test client with full business flow visibility."""

    def __init__(self) -> None:
        self.system = CollectAgentSystem.from_config()
        self._users: dict[str, UserState] = {}

    def create_user(
        self,
        user_id: str,
        name: str,
        overdue_days: int,
        amount_due: float,
        occupation: str | None = None,
    ) -> UserState:
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
        self._users[user_id] = state
        return state

    async def send_event(
        self,
        user_id: str,
        event_type: EventType,
        payload: dict | None = None,
    ) -> SkillResult | None:
        """Send event directly through session to capture SkillResult."""
        event = Event(
            user_id=user_id,
            type=event_type,
            payload=payload or {},
        )
        session = self.system.session_manager.get_or_create(user_id)
        result = await session.handle_event(event)
        # Sync local cache
        self._users[user_id] = session.user_state
        return result

    def get_user(self, user_id: str) -> UserState | None:
        if user_id in self._users:
            return self._users[user_id]
        state = self.system.store.load(user_id)
        if state:
            self._users[user_id] = state
        return state

    def list_users(self) -> list[UserState]:
        return list(self._users.values())

    def print_divider(self, title: str = "") -> None:
        width = 60
        if title:
            pad = (width - len(title) - 4) // 2
            print(f"\n{'=' * pad} {title} {'=' * pad}")
        else:
            print(f"\n{'=' * width}")

    def print_user_summary(self, state: UserState) -> None:
        print(f"  用户ID:     {state.user_id}")
        print(f"  姓名:       {state.profile.name}")
        print(f"  逾期:       {state.profile.overdue_days} 天")
        print(f"  金额:       ¥{state.profile.amount_due}")
        print(f"  职业:       {state.profile.occupation or '无'}")
        print(f"  敏感职业:   {'是' if state.profile.is_sensitive else '否'}")

    def print_session_detail(self, user_id: str) -> None:
        state = self.get_user(user_id)
        if not state:
            print(f"用户 {user_id} 不存在")
            return

        self.print_divider(f"用户详情: {user_id}")
        print(f"  会话状态:   {state.session_state}")
        print(f"  当前意图:   {state.conversation.current_intent or '无'}")
        print(f"  协商轮数:   {state.conversation.negotiation_round}")
        print(f"  配额使用:   {state.quota_usage}")
        print(f"  暂停至:     {state.paused_until or '未暂停'}")

        msgs = state.conversation.messages
        print(f"\n  对话历史 ({len(msgs)} 条):")
        if not msgs:
            print("    (空)")
        for msg in msgs:
            ts = msg.timestamp.strftime("%H:%M:%S") if msg.timestamp else "?"
            direction = "🤖" if msg.direction == "outbound" else "👤"
            content = msg.content[:200]
            print(f"    [{ts}] {direction} [{msg.channel}] {content}")

    def print_skill_result(self, result: SkillResult | None) -> None:
        if not result:
            print("  (无 SkillResult 返回)")
            return
        self.print_divider("Skill 执行结果")
        print(f"  状态:       {result.status}")
        print(f"  回复内容:   {result.response_text or '(空)'}")
        print(f"  新会话状态: {result.new_session_state or '(无变更)'}")
        print(f"  是否升级:   {result.escalation}")
        print(f"  需要跟进:   {result.requires_follow_up}")
        print(f"  思考过程:   {result.thinking[:300]}")


async def menu() -> None:
    client = TestClient()

    while True:
        client.print_divider("催收 Agent 交互式测试客户端")
        print("  1. 创建测试用户")
        print("  2. 查看用户列表")
        print("  3. 查看用户详细状态")
        print("  4. 触发催收 (scheduled_outreach)")
        print("  5. 模拟用户回复")
        print("  6. 模拟用户支付")
        print("  7. 模拟静默超时")
        print("  8. 运行完整 Demo 流程")
        print("  0. 退出")
        print("-" * 60)

        choice = safe_input("选择操作: ")

        if choice == "1":
            uid = safe_input("  用户ID (默认 test_001): ") or "test_001"
            name = safe_input("  姓名 (默认 张三): ") or "张三"
            overdue = int(safe_input("  逾期天数 (默认 5): ") or "5")
            amount = float(safe_input("  金额 (默认 1000): ") or "1000")
            occ = safe_input("  职业 (直接回车=无): ") or None
            state = client.create_user(uid, name, overdue, amount, occ)
            client.print_divider("创建成功")
            client.print_user_summary(state)

        elif choice == "2":
            users = client.list_users()
            if not users:
                print("暂无用户")
            else:
                client.print_divider("用户列表")
                for s in users:
                    flag = "🔒" if s.profile.is_sensitive else "  "
                    print(
                        f"  {flag} {s.user_id}: {s.profile.name}, "
                        f"逾期{s.profile.overdue_days}天, "
                        f"¥{s.profile.amount_due}, "
                        f"状态={s.session_state}"
                    )

        elif choice == "3":
            uid = safe_input("  用户ID: ")
            client.print_session_detail(uid)

        elif choice == "4":
            uid = safe_input("  用户ID: ")
            print(f"\n→ 触发催收: {uid}")
            result = await client.send_event(uid, EventType.SCHEDULED_OUTREACH)
            client.print_skill_result(result)
            client.print_session_detail(uid)

        elif choice == "5":
            uid = safe_input("  用户ID: ")
            msg = safe_input("  用户消息: ")
            print(f"\n→ 用户回复: {msg}")
            result = await client.send_event(
                uid, EventType.USER_REPLIED, {"message": msg}
            )
            client.print_skill_result(result)
            client.print_session_detail(uid)

        elif choice == "6":
            uid = safe_input("  用户ID: ")
            amt = safe_input("  支付金额 (默认 1000): ") or "1000"
            print(f"\n→ 模拟支付: ¥{amt}")
            result = await client.send_event(
                uid, EventType.USER_PAYMENT_SUCCESS, {"amount": float(amt)}
            )
            client.print_skill_result(result)
            client.print_session_detail(uid)

        elif choice == "7":
            uid = safe_input("  用户ID: ")
            print(f"\n→ 静默超时: {uid}")
            result = await client.send_event(
                uid, EventType.SILENCE_TIMEOUT, {"tier": 0, "seconds": 600}
            )
            client.print_skill_result(result)
            client.print_session_detail(uid)

        elif choice == "8":
            uid = safe_input("  用户ID (默认 test_001): ") or "test_001"
            print(f"\n→ 运行完整 Demo: {uid}")

            # Step 1: create user if not exists
            if not client.get_user(uid):
                client.create_user(uid, "张三", 5, 1000.0)
                print("  [1] 创建用户")
            else:
                print("  [1] 用户已存在")

            # Step 2: outreach
            print("  [2] 触发催收...")
            result = await client.send_event(uid, EventType.SCHEDULED_OUTREACH)
            print(f"      → 回复: {result.response_text[:100] if result else 'N/A'}")

            # Step 3: user reply
            msg = safe_input("  [3] 模拟用户回复 (默认 '我会还的'): ") or "我会还的"
            print(f"      → 用户: {msg}")
            result = await client.send_event(uid, EventType.USER_REPLIED, {"message": msg})
            print(f"      → 识别意图: {client.get_user(uid).conversation.current_intent}")
            print(f"      → 回复: {result.response_text[:100] if result else 'N/A'}")

            # Step 4: silence timeout
            cont = safe_input("  [4] 触发静默超时? (回车=是): ")
            if cont == "":
                result = await client.send_event(
                    uid, EventType.SILENCE_TIMEOUT, {"tier": 0, "seconds": 600}
                )
                print(f"      → 回复: {result.response_text[:100] if result else 'N/A'}")

            # Step 5: payment
            cont = safe_input("  [5] 模拟支付? (回车=是): ")
            if cont == "":
                result = await client.send_event(
                    uid, EventType.USER_PAYMENT_SUCCESS, {"amount": 1000.0}
                )
                print(f"      → 状态: {client.get_user(uid).session_state}")

            client.print_session_detail(uid)

        elif choice == "0":
            break

        else:
            print("无效选择")


if __name__ == "__main__":
    asyncio.run(menu())
