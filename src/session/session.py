import logging
from datetime import datetime, timezone

from src.core.constants import (
    ChannelState,
    ChannelType,
    EventType,
    Intent,
    SessionState,
)
from src.core.models import Event, Message, UserState
from src.channels.registry import create_default_registry
from src.compliance.checker import ComplianceChecker
from src.llm.clients import MockLLMClient
from src.llm.base import LLMClient
from src.orchestrator.lock import InteractionLock
from src.orchestrator.orchestrator import Orchestrator
from src.quota.manager import QuotaManager
from src.session.state_machine import SessionStateMachine
from src.storage.sqlite_store import SQLiteStore
from src.strategy.detector import IntentDetector
from src.strategy.engine import StrategyEngine

logger = logging.getLogger(__name__)


class CollectionSession:
    def __init__(
        self,
        user_id: str,
        state: UserState,
        strategy_engine: StrategyEngine | None = None,
        orchestrator: Orchestrator | None = None,
        quota_manager: QuotaManager | None = None,
        compliance_checker: ComplianceChecker | None = None,
        llm_client: LLMClient | None = None,
        storage: SQLiteStore | None = None,
    ):
        self.user_id = user_id
        self.state = state
        self.state_machine = SessionStateMachine()
        self.channels = create_default_registry()
        self.lock = InteractionLock()
        self.context = {}
        self.last_interaction_at: datetime | None = None

        self.strategy_engine = strategy_engine or StrategyEngine()
        self.orchestrator = orchestrator or Orchestrator()
        self.quota_manager = quota_manager or QuotaManager()
        self.compliance_checker = compliance_checker or ComplianceChecker()
        self.llm_client = llm_client or MockLLMClient()
        self.storage = storage or SQLiteStore()
        self.intent_detector = IntentDetector()

    async def handle_event(self, event: Event) -> None:
        try:
            if event.type in {
                EventType.SCHEDULED_OUTREACH,
                EventType.REMINDER_DUE,
                EventType.USER_LOGIN,
            }:
                await self._handle_outreach_event(event)
            elif event.type in {
                EventType.USER_REPLIED,
                EventType.CALL_CONNECTED,
                EventType.CALL_NO_ANSWER,
                EventType.MESSAGE_DELIVERED,
            }:
                self._record_interaction()
                await self._handle_interaction_event(event)
            elif event.type == EventType.SILENCE_TIMEOUT:
                await self._handle_silence_timeout(event)
            elif event.type == EventType.USER_PAYMENT_SUCCESS:
                await self._handle_payment_success(event)
            elif event.type in {
                EventType.COMPLIANCE_VIOLATION,
                EventType.QUOTA_EXHAUSTED,
            }:
                await self._handle_deferred_event(event)
            else:
                logger.info("Unhandled event type: %s", event.type.value)
        except Exception:
            logger.exception("Error handling event %s", event.type.value)

    def _record_interaction(self) -> None:
        self.last_interaction_at = datetime.now(timezone.utc)
        # Also notify scheduler's tracker if available
        if hasattr(self, '_timeout_tracker') and self._timeout_tracker is not None:
            self._timeout_tracker.record_interaction(self.user_id)

    async def _handle_outreach_event(self, event: Event) -> None:
        # 1. Check compliance
        if not self.compliance_checker.is_within_valid_hours():
            logger.info("Outreach blocked: outside valid hours")
            return

        # 2. Check quota
        can_contact, reason = self.orchestrator.can_contact_user(self.state.profile)
        if not can_contact:
            logger.info("Outreach blocked: %s", reason)
            return

        # 3. Select channel
        channel_type = self.orchestrator.select_channel(self.state.profile)
        if channel_type is None:
            logger.info("No channel available for outreach")
            return

        # 4. Acquire interaction lock
        arbitration = self.orchestrator.arbitrate(self.user_id, channel_type)
        if arbitration != "granted":
            logger.info("Lock not granted for channel %s", channel_type.value)
            return

        # 5. Select strategy
        intent = Intent.INEFFECTIVE_CONTACT
        strategy = self.strategy_engine.select_strategy(self.state.profile, intent)

        # 6. Generate response
        response_text = await self._generate_response(strategy)

        # 7. Send via selected channel
        channel = self.channels.get(channel_type)
        if channel is not None:
            await channel.send(self.user_id, response_text)
            self.channels.set_state(channel_type, ChannelState.OUTGOING)

        # 8. Record quota usage
        if channel_type == ChannelType.VOICE:
            self.quota_manager.record_call_self(self.user_id)
        elif channel_type == ChannelType.CHATBOT:
            self.quota_manager.record_chat(self.user_id)

        # 9. Update state machine
        if self.state_machine.can_transition(SessionState.OUTREACH_START):
            self.state_machine.transition(SessionState.OUTREACH_START)
        if self.state_machine.can_transition(SessionState.INTENT_DETECTED):
            self.state_machine.transition(SessionState.INTENT_DETECTED)

        # 10. Save state
        self._sync_state()
        self.storage.save(self.state)

    async def _handle_interaction_event(self, event: Event) -> None:
        channel_type_str = event.payload.get("channel", "chatbot")
        try:
            channel_type = ChannelType(channel_type_str)
        except ValueError:
            channel_type = ChannelType.CHATBOT

        # Update channel state
        if event.type == EventType.CALL_CONNECTED:
            self.channels.set_state(channel_type, ChannelState.INTERACTING)
            arbitration = self.orchestrator.arbitrate(self.user_id, channel_type)
            if arbitration == "granted":
                self.lock.acquire(channel_type)
            if self.state_machine.can_transition(SessionState.INTENT_DETECTED):
                self.state_machine.transition(SessionState.INTENT_DETECTED)
        elif event.type == EventType.CALL_NO_ANSWER:
            self.channels.set_state(channel_type, ChannelState.IDLE)
            intent = Intent.INEFFECTIVE_CONTACT
            strategy = self.strategy_engine.select_strategy(self.state.profile, intent)
            response_text = await self._generate_response(strategy)
            # Try next channel
            next_channel = self._select_next_channel(channel_type)
            if next_channel is not None:
                channel = self.channels.get(next_channel)
                if channel is not None:
                    await channel.send(self.user_id, response_text)
                    self.channels.set_state(next_channel, ChannelState.OUTGOING)
            self.state.conversation.current_intent = Intent.INEFFECTIVE_CONTACT.value
        elif event.type == EventType.USER_REPLIED:
            self.channels.set_state(channel_type, ChannelState.INTERACTING)
            user_message = event.payload.get("content", "")
            # Detect intent
            detected = self.intent_detector.detect(user_message)
            # Try LLM fallback
            try:
                llm_intent_str = await self.llm_client.detect_intent(
                    user_message, {}
                )
                llm_intent = self._parse_intent(llm_intent_str)
                if llm_intent != Intent.INEFFECTIVE_CONTACT:
                    detected = llm_intent
            except Exception:
                logger.exception("LLM intent detection failed, using rule-based")

            self.state.conversation.current_intent = detected.value
            self.state.conversation.add_message(
                Message(
                    channel=channel_type.value,
                    direction="inbound",
                    content=user_message,
                )
            )
            self.state.conversation.negotiation_round += 1

            # Select follow-up strategy
            strategy = self.strategy_engine.select_strategy(self.state.profile, detected)
            response_text = await self._generate_response(strategy)
            channel = self.channels.get(channel_type)
            if channel is not None:
                await channel.send(self.user_id, response_text)
                self.channels.set_state(channel_type, ChannelState.WAITING_REPLY)

            if self.state_machine.can_transition(SessionState.FOLLOW_UP):
                self.state_machine.transition(SessionState.FOLLOW_UP)
        elif event.type == EventType.MESSAGE_DELIVERED:
            current = self.channels.get_state(channel_type)
            if current == ChannelState.OUTGOING:
                self.channels.set_state(channel_type, ChannelState.WAITING_REPLY)

        self._sync_state()
        self.storage.save(self.state)

    async def _handle_silence_timeout(self, _event: Event) -> None:
        intent = Intent.INEFFECTIVE_CONTACT
        self.state.conversation.current_intent = intent.value

        strategy = self.strategy_engine.select_strategy(self.state.profile, intent)
        response_text = await self._generate_response(strategy)

        # Re-engage: try channels in priority order
        for channel_type in (ChannelType.CHATBOT, ChannelType.PUSH, ChannelType.VOICE):
            channel = self.channels.get(channel_type)
            if channel is None:
                continue
            can_contact, _ = self.orchestrator.can_contact_user(self.state.profile)
            if not can_contact:
                continue
            arbitration = self.orchestrator.arbitrate(self.user_id, channel_type)
            if arbitration == "granted":
                await channel.send(self.user_id, response_text)
                self.channels.set_state(channel_type, ChannelState.OUTGOING)
                if channel_type == ChannelType.VOICE:
                    self.quota_manager.record_call_self(self.user_id)
                elif channel_type == ChannelType.CHATBOT:
                    self.quota_manager.record_chat(self.user_id)
                break

        if self.state_machine.can_transition(SessionState.FOLLOW_UP):
            self.state_machine.transition(SessionState.FOLLOW_UP)

        self._sync_state()
        self.storage.save(self.state)

    async def _handle_payment_success(self, _event: Event) -> None:
        if self.state_machine.can_transition(SessionState.RESOLVED):
            self.state_machine.transition(SessionState.RESOLVED)

        # Send confirmation
        confirmation = "感谢您的还款，您的账单已结清。如有任何问题，请联系客服。"
        channel_type = ChannelType.CHATBOT
        channel = self.channels.get(channel_type)
        if channel is not None:
            await channel.send(self.user_id, confirmation)

        # Release lock and close session
        self.orchestrator.release_lock(self.user_id)
        self.lock.release()

        self._sync_state()
        self.storage.save(self.state)

    async def _handle_deferred_event(self, event: Event) -> None:
        logger.info("Deferred event %s for user %s", event.type.value, self.user_id)

    async def _generate_response(self, strategy: dict) -> str:
        context = {
            "round": self.state.conversation.negotiation_round,
            "planned_date": "",
            "user_name": self.state.profile.name,
        }
        try:
            return await self.llm_client.generate_strategy_response(strategy, context)
        except Exception:
            logger.exception("LLM response generation failed, using template fallback")
            return self.strategy_engine.get_response(
                self.state.profile, strategy, context
            )

    def _parse_intent(self, intent_str: str) -> Intent:
        mapping = {
            "willing_to_pay": Intent.WILLING_TO_PAY,
            "unwilling_to_pay": Intent.UNWILLING_TO_PAY,
            "ineffective_contact": Intent.INEFFECTIVE_CONTACT,
            "complaint": Intent.COMPLAINT,
            "payment_method_inquiry": Intent.PAYMENT_METHOD_INQUIRY,
            "operation_inquiry": Intent.OPERATION_INQUIRY,
            "request_info": Intent.PAYMENT_METHOD_INQUIRY,
        }
        return mapping.get(intent_str.lower(), Intent.INEFFECTIVE_CONTACT)

    def _select_next_channel(self, current: ChannelType) -> ChannelType | None:
        order = [ChannelType.CHATBOT, ChannelType.PUSH, ChannelType.VOICE]
        try:
            idx = order.index(current)
            for ch in order[idx + 1 :]:
                if self.channels.get(ch) is not None:
                    return ch
        except ValueError:
            pass
        return None

    def _sync_state(self) -> None:
        self.state.session_state = self.state_machine.current.value
        self.state.channel_states = self.channels.get_all_states()
