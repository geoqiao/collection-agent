from collect_agent.core.constants import EventType, ChannelType, Intent
from collect_agent.core.models import UserProfile, Event, Message


def test_event_type_has_required_events():
    assert EventType.SCHEDULED_OUTREACH is not None
    assert EventType.USER_LOGIN is not None
    assert EventType.CALL_CONNECTED is not None
    assert EventType.USER_REPLIED is not None


def test_channel_type_values():
    assert ChannelType.VOICE.value == "voice"
    assert ChannelType.CHATBOT.value == "chatbot"
    assert ChannelType.PUSH.value == "push"


def test_intent_values():
    assert Intent.WILLING_TO_PAY.value == "willing_to_pay"
    assert Intent.UNWILLING_TO_PAY.value == "unwilling_to_pay"
    assert Intent.INEFFECTIVE_CONTACT.value == "ineffective_contact"
    assert Intent.COMPLAINT.value == "complaint"
    assert Intent.PAYMENT_METHOD_INQUIRY.value == "payment_method_inquiry"
    assert Intent.OPERATION_INQUIRY.value == "operation_inquiry"


def test_user_profile_creation():
    user = UserProfile(user_id="u001", name="张三", phone="13800138000")
    assert user.user_id == "u001"
    assert user.is_sensitive is False


def test_user_profile_sensitive_occupation():
    user = UserProfile(user_id="u002", name="李四", occupation="律师")
    assert user.is_sensitive is True


def test_event_creation():
    event = Event(user_id="u001", type=EventType.USER_LOGIN, payload={})
    assert event.user_id == "u001"
    assert event.type == EventType.USER_LOGIN


def test_message_creation():
    msg = Message(channel="chatbot", direction="outbound", content="请尽快还款")
    assert msg.channel == "chatbot"
    assert msg.direction == "outbound"
