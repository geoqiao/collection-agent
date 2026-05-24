from datetime import datetime, timezone

from collect_agent.core.constants import EventType
from collect_agent.core.models import Event
from collect_agent.session.timeout_tracker import SilenceTimeoutTracker


class OutreachScheduler:
    def __init__(self, system):
        self.system = system
        self.tracker = SilenceTimeoutTracker()

    def _ensure_tracker_wired(self, session):
        """Wire the tracker into the session so interactions are recorded."""
        if not hasattr(session, '_timeout_tracker') or session._timeout_tracker is not self.tracker:
            session._timeout_tracker = self.tracker

    async def scan_and_outreach(self):
        """Scan all users and trigger outreach for those who need it."""
        states = self.system.store.load_all()
        for state in states:
            # Skip paused users
            if state.paused_until and state.paused_until > datetime.now(timezone.utc):
                continue
            profile = state.profile
            if profile.overdue_days > 0 and state.session_state != "resolved":
                event = Event(
                    user_id=state.user_id,
                    type=EventType.SCHEDULED_OUTREACH,
                )
                await self.system.router.route_async(event)

    async def check_silence_timeouts(self):
        """Check all sessions for silence timeouts."""
        for user_id, session in self.system.session_manager._sessions.items():
            # Skip paused users
            if session.state.paused_until and session.state.paused_until > datetime.now(timezone.utc):
                continue
            self._ensure_tracker_wired(session)
            tier_idx = await self.tracker.check_timeout(session)
            if tier_idx is not None:
                event = Event(
                    user_id=user_id,
                    type=EventType.SILENCE_TIMEOUT,
                    payload={"tier": tier_idx, "seconds": SilenceTimeoutTracker.TIERS[tier_idx]},
                )
                await self.system.router.route_async(event)
