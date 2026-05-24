import asyncio
from datetime import datetime, timezone

from collect_agent.agent.session import AgentSession
from collect_agent.session.session import CollectionSession


class SilenceTimeoutTracker:
    TIERS = [600, 3600, 86400, 259200]  # 10min, 1h, 1day, 3days in seconds

    def __init__(self):
        self._emitted_tiers: dict[str, set[int]] = {}
        self._mutex = asyncio.Lock()

    def record_interaction(self, user_id: str) -> None:
        self._emitted_tiers.pop(user_id, None)

    async def check_timeout(
        self, session: CollectionSession | AgentSession
    ) -> int | None:
        user_id = session.user_id
        last = session.last_outreach_at
        if last is None:
            return None

        elapsed = (datetime.now(timezone.utc) - last).total_seconds()

        async with self._mutex:
            emitted = self._emitted_tiers.setdefault(user_id, set())

            for idx, tier in enumerate(self.TIERS):
                if elapsed >= tier and idx not in emitted:
                    emitted.add(idx)
                    return idx

        return None
