from src.core.constants import EventType, ChannelType, Intent, SessionState, ChannelState


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
