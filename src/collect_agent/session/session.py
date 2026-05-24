import logging
from datetime import datetime, timezone

from datetime import timedelta

from collect_agent.core.constants import (
    ChannelState,
    ChannelType,
    EventType,
    Intent,
    SessionState,
)
from collect_agent.core.exceptions import (
    ChannelError,
    ComplianceViolationError,
    QuotaExceededError,
    StorageError,
)
from collect_agent.core.models import Event, Message, UserState
from collect_agent.channels.registry import create_default_registry
from collect_agent.compliance.checker import ComplianceChecker
from collect_agent.llm.clients import MockLLMClient
from collect_agent.llm.base import LLMClient
from collect_agent.orchestrator.orchestrator import Orchestrator
from collect_agent.quota.manager import QuotaManager
from collect_agent.session.state_machine import SessionStateMachine
from collect_agent.context.manager import ContextManager
from collect_agent.storage.sqlite_store import SQLiteStore
from collect_agent.strategy.detector import IntentDetector
from collect_agent.strategy.engine import StrategyEngine
from collect_agent.strategy.strategies import STRATEGIES

logger = logging.getLogger(__name__)


class CollectionSession:
    """Legacy session handler using static strategies and keyword intent detection.

    .. deprecated::
        Use AgentSession (src.agent.session.AgentSession) instead.
        CollectionSession is kept for backward compatibility during migration.
    """

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
        self.context = {}
        self.last_interaction_at: datetime | None = None
        self.last_outreach_at: datetime | None = None

        self.strategy_engine = strategy_engine or StrategyEngine()
        self.quota_manager = quota_manager or QuotaManager()
        self.compliance_checker = compliance_checker or ComplianceChecker()
        self.orchestrator = orchestrator or Orchestrator(
            quota_manager=self.quota_manager,
            compliance_checker=self.compliance_checker,
        )
        self.llm_client = llm_client or MockLLMClient()
        self.storage = storage or SQLiteStore()
        self.intent_detector = IntentDetector()
        self.context_manager = ContextManager(user_id=user_id)

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
            elif event.type == EventType.COMPLAINT:
                await self._handle_complaint(event)
            elif event.type in {
                EventType.COMPLIANCE_VIOLATION,
                EventType.QUOTA_EXHAUSTED,
            }:
                await self._handle_deferred_event(event)
            else:
                logger.info("Unhandled event type: %s", event.type.value)
        except ComplianceViolationError as e:
            logger.warning("Compliance violation for %s: %s", self.user_id, e)
        except QuotaExceededError as e:
            logger.info("Quota exceeded for %s: %s", self.user_id, e)
        except ChannelError as e:
            logger.error("Channel error for %s: %s", self.user_id, e)
        except StorageError as e:
            logger.error("Storage error for %s: %s", self.user_id, e)
        except Exception:
            logger.exception("Unexpected error handling event %s", event.type.value)

    def _record_interaction(self) -> None:
        self.last_interaction_at = datetime.now(timezone.utc)
        # Also notify scheduler's tracker if available
        if hasattr(self, "_timeout_tracker") and self._timeout_tracker is not None:
            self._timeout_tracker.record_interaction(self.user_id)

    def _record_outreach(self) -> None:
        self.last_outreach_at = datetime.now(timezone.utc)

    async def _handle_outreach_event(self, event: Event) -> None:
        # 1. Check compliance
        if not self.compliance_checker.is_within_valid_hours():
            logger.info("Outreach blocked: outside valid hours")
            return

        # 2. Check quota
        can_contact, reason = self.orchestrator.is_within_compliance_hours()
        if not can_contact:
            logger.info("Outreach blocked: %s", reason)
            return

        # 3. Select channel
        channel_type = await self.orchestrator.select_channel(self.state.profile)
        if channel_type is None:
            logger.info("No channel available for outreach")
            return

        # 4. Acquire interaction lock
        arbitration = await self.orchestrator.arbitrate(self.user_id, channel_type)
        if arbitration != "granted":
            logger.info("Lock not granted for channel %s", channel_type.value)
            return

        # 5. Select strategy
        if self.state.profile.is_sensitive:
            strategy = STRATEGIES["standard_reminder"]
        else:
            intent = Intent.INEFFECTIVE_CONTACT
            strategy = self.strategy_engine.select_strategy(self.state.profile, intent)

        # 6. Generate response
        response_text = await self._generate_response(strategy)

        # 7. Content audit before sending
        is_clean, reason = self.compliance_checker.audit_content(response_text)
        if not is_clean:
            logger.warning("Content audit failed: %s", reason)
            response_text = self.compliance_checker.get_standard_message(
                self.state.profile
            )

        # 8. Send via selected channel
        channel = self.channels.get(channel_type)
        if channel is not None:
            await channel.send(self.user_id, response_text)
            self.channels.set_state(channel_type, ChannelState.OUTGOING)
            self._record_outreach()

        # 8. Record quota usage
        if channel_type == ChannelType.VOICE:
            await self.quota_manager.record_call_self(self.user_id)
        elif channel_type == ChannelType.CHATBOT:
            await self.quota_manager.record_chat(self.user_id)

        # 8.5. Record contact context
        self.context_manager.record_contact(channel_type.value, False)

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
            arbitration = await self.orchestrator.arbitrate(self.user_id, channel_type)
            if arbitration == "granted":
                lock = await self.orchestrator.get_lock(self.user_id)
                lock.acquire(channel_type)
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
            channel = self.channels.get(channel_type)
            if channel is not None and hasattr(channel, "receive"):
                user_message = event.payload.get("content", "")
                await channel.receive(self.user_id, user_message)
            self.channels.set_state(channel_type, ChannelState.INTERACTING)
            user_message = event.payload.get("content", "")
            # Detect intent
            detected = self.intent_detector.detect(user_message)
            # Try LLM fallback
            try:
                llm_intent_str = await self.llm_client.detect_intent(user_message, {})
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

            # Record context
            self.context_manager.record_contact(channel_type.value, True)
            self.context_manager.record_intent(detected.value)

            # Select follow-up strategy
            if self.state.profile.is_sensitive:
                strategy = STRATEGIES["standard_reminder"]
            else:
                strategy = self.strategy_engine.select_strategy(
                    self.state.profile, detected
                )

                # Check max rounds (only for non-sensitive users in negotiation)
                max_rounds = strategy.get("max_rounds", 3)
                if self.state.conversation.negotiation_round >= max_rounds:
                    # Escalate: switch to standard reminder or pause
                    logger.info(
                        "Max rounds reached for user %s, escalating", self.user_id
                    )
                    strategy = STRATEGIES.get(
                        Intent.COMPLAINT, STRATEGIES["standard_reminder"]
                    )

            response_text = await self._generate_response(strategy)

            # Content audit before sending
            is_clean, reason = self.compliance_checker.audit_content(response_text)
            if not is_clean:
                logger.warning("Content audit failed: %s", reason)
                response_text = self.compliance_checker.get_standard_message(
                    self.state.profile
                )

            channel = self.channels.get(channel_type)
            if channel is not None:
                await channel.send(self.user_id, response_text)
                self.channels.set_state(channel_type, ChannelState.WAITING_REPLY)
                self._record_outreach()
                # Record outbound message in context window
                self.context_manager.add_message(
                    Message(
                        channel=channel_type.value,
                        direction="outbound",
                        content=response_text,
                    )
                )

            # Dynamic quota adjustment
            await self.quota_manager.set_chat_replied(self.user_id)

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

        # Content audit before sending
        is_clean, reason = self.compliance_checker.audit_content(response_text)
        if not is_clean:
            logger.warning("Content audit failed: %s", reason)
            response_text = self.compliance_checker.get_standard_message(
                self.state.profile
            )

        # Re-engage: try channels in priority order
        for channel_type in (ChannelType.CHATBOT, ChannelType.PUSH, ChannelType.VOICE):
            channel = self.channels.get(channel_type)
            if channel is None:
                continue
            can_contact, _ = self.orchestrator.is_within_compliance_hours()
            if not can_contact:
                continue
            arbitration = await self.orchestrator.arbitrate(self.user_id, channel_type)
            if arbitration == "granted":
                await channel.send(self.user_id, response_text)
                self.channels.set_state(channel_type, ChannelState.OUTGOING)
                self._record_outreach()
                if channel_type == ChannelType.VOICE:
                    await self.quota_manager.record_call_self(self.user_id)
                elif channel_type == ChannelType.CHATBOT:
                    await self.quota_manager.record_chat(self.user_id)
                break

        if self.state_machine.can_transition(SessionState.FOLLOW_UP):
            self.state_machine.transition(SessionState.FOLLOW_UP)

        self._sync_state()
        self.storage.save(self.state)

    async def _handle_payment_success(self, _event: Event) -> None:
        if self.state_machine.can_transition(SessionState.RESOLVED):
            self.state_machine.transition(SessionState.RESOLVED)

        # Mark any pending promises as kept
        for i, promise in enumerate(self.context_manager.user_context.payment_promises):
            if promise["status"] == "pending":
                self.context_manager.user_context.mark_promise_kept(i)

        # Send confirmation
        confirmation = "感谢您的还款，您的账单已结清。如有任何问题，请联系客服。"
        channel_type = ChannelType.CHATBOT
        channel = self.channels.get(channel_type)
        if channel is not None:
            await channel.send(self.user_id, confirmation)

        # Release lock and close session
        self.orchestrator.release_and_cleanup_lock(self.user_id)

        self._sync_state()
        self.storage.save(self.state)

    async def _handle_complaint(self, event: Event) -> None:
        # Pause collection for 48 hours
        self.state.paused_until = datetime.now(timezone.utc) + timedelta(hours=48)

        # Send apology and transfer message
        strategy = STRATEGIES[Intent.COMPLAINT]
        response_text = await self._generate_response(strategy)

        # Content audit before sending
        is_clean, reason = self.compliance_checker.audit_content(response_text)
        if not is_clean:
            logger.warning("Content audit failed: %s", reason)
            response_text = self.compliance_checker.get_standard_message(
                self.state.profile
            )

        channel = self.channels.get(ChannelType.CHATBOT)
        if channel is not None:
            await channel.send(self.user_id, response_text)

        # Transition to resolved (paused state)
        if self.state_machine.can_transition(SessionState.RESOLVED):
            self.state_machine.transition(SessionState.RESOLVED)

        self._sync_state()
        self.storage.save(self.state)

    async def _handle_deferred_event(self, event: Event) -> None:
        logger.info("Deferred event %s for user %s", event.type.value, self.user_id)

    async def _generate_response(self, strategy: dict) -> str:
        context = {
            "round": self.state.conversation.negotiation_round,
            "planned_date": "",
            "user_name": self.state.profile.name,
            "user_context": self.context_manager.get_user_context_summary(),
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
        # Sync conversation state
        self.state.conversation.current_intent = getattr(
            self.state.conversation, "current_intent", None
        )
        # Sync quota usage from manager
        usage = self.quota_manager.get_usage_for_user(self.user_id)
        if usage and hasattr(usage, "model_dump"):
            self.state.quota_usage = usage.model_dump()
