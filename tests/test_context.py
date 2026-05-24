from collect_agent.context.window import ContextWindow
from collect_agent.context.user_context import UserContext
from collect_agent.context.manager import ContextManager
from collect_agent.core.models import Message


class TestContextWindow:
    def test_add_message(self):
        cw = ContextWindow(max_messages=3)
        cw.add_message(Message(channel="chatbot", direction="outbound", content="hi"))
        assert cw.message_count == 1

    def test_sliding_window_truncates(self):
        cw = ContextWindow(max_messages=3)
        for i in range(5):
            cw.add_message(Message(channel="chatbot", direction="outbound", content=f"msg{i}"))
        assert cw.message_count == 3
        assert cw.get_messages()[0].content == "msg2"

    def test_get_messages_for_llm(self):
        cw = ContextWindow()
        cw.add_message(Message(channel="chatbot", direction="outbound", content="hello"))
        msgs = cw.get_messages_for_llm()
        assert msgs[0]["role"] == "assistant"
        assert msgs[0]["content"] == "hello"

    def test_get_messages_for_llm_inbound(self):
        cw = ContextWindow()
        cw.add_message(Message(channel="chatbot", direction="inbound", content="hi there"))
        msgs = cw.get_messages_for_llm()
        assert msgs[0]["role"] == "user"
        assert msgs[0]["content"] == "hi there"

    def test_clear(self):
        cw = ContextWindow()
        cw.add_message(Message(channel="chatbot", direction="outbound", content="hello"))
        cw.clear()
        assert cw.message_count == 0

    def test_is_full(self):
        cw = ContextWindow(max_messages=2)
        assert not cw.is_full
        cw.add_message(Message(channel="chatbot", direction="outbound", content="a"))
        cw.add_message(Message(channel="chatbot", direction="outbound", content="b"))
        assert cw.is_full


class TestUserContext:
    def test_response_rate(self):
        uc = UserContext(user_id="u1")
        uc.record_contact("chatbot", True)
        uc.record_contact("voice", False)
        assert uc.get_response_rate() == 0.5

    def test_dominant_intent(self):
        uc = UserContext(user_id="u1")
        uc.record_intent("willing_to_pay")
        uc.record_intent("willing_to_pay")
        uc.record_intent("unwilling_to_pay")
        assert uc.get_dominant_intent() == "willing_to_pay"

    def test_escalation(self):
        uc = UserContext(user_id="u1")
        uc.escalate()
        uc.escalate()
        uc.escalate()  # Max is 2
        assert uc.escalation_level == 2

    def test_payment_promise(self):
        uc = UserContext(user_id="u1")
        uc.record_payment_promise("2024-01-01", 100.0)
        assert len(uc.payment_promises) == 1
        assert uc.payment_promises[0]["status"] == "pending"
        uc.mark_promise_kept(0)
        assert uc.payment_promises[0]["status"] == "kept"

    def test_preferred_channel(self):
        uc = UserContext(user_id="u1")
        uc.record_contact("voice", True)
        assert uc.preferred_channel == "voice"
        uc.record_contact("chatbot", True)
        assert uc.preferred_channel == "chatbot"

    def test_get_dominant_intent_empty(self):
        uc = UserContext(user_id="u1")
        assert uc.get_dominant_intent() is None


class TestContextManager:
    def test_to_dict_roundtrip(self):
        cm = ContextManager(user_id="u1")
        cm.add_message(Message(channel="chatbot", direction="outbound", content="hi"))
        cm.record_intent("willing_to_pay")
        data = cm.to_dict()
        restored = ContextManager.from_dict(data)
        assert restored.user_id == "u1"
        assert restored.window.message_count == 1

    def test_get_user_context_summary(self):
        cm = ContextManager(user_id="u1")
        cm.record_contact("chatbot", True)
        cm.record_intent("willing_to_pay")
        summary = cm.get_user_context_summary()
        assert "User ID: u1" in summary
        assert "Total contacts: 1" in summary
        assert "Response rate: 100%" in summary
        assert "Recent dominant intent: willing_to_pay" in summary

    def test_get_llm_context(self):
        cm = ContextManager(user_id="u1")
        cm.add_message(Message(channel="chatbot", direction="outbound", content="hello"))
        msgs = cm.get_llm_context()
        assert len(msgs) == 1
        assert msgs[0]["role"] == "assistant"
