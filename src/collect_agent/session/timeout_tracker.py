"""Silence timeout tracker with persisted state.

Emitted timeout tiers are stored in UserState.silence_timeout_emitted
so they survive process restarts.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from collect_agent.core.models import UserState


class SilenceTimeoutTracker:
    TIERS = [600, 3600, 86400, 259200]  # 10min, 1h, 1day, 3days in seconds

    def __init__(self):
        self._mutex = asyncio.Lock()

    def record_interaction(self, state: UserState) -> None:
        """Clear emitted tiers when user interacts (reply, payment, etc.)."""
        state.silence_timeout_emitted = []

    async def check_timeout(self, state: UserState) -> int | None:
        """Check if a silence timeout tier should trigger for this user.

        Uses UserState.silence_timeout_emitted for persistence across restarts.
        Returns the tier index if a new timeout fires, None otherwise.
        """
        last = state.last_outreach_at
        if last is None:
            return None

        elapsed = (datetime.now(UTC) - last).total_seconds()

        async with self._mutex:
            emitted = set(state.silence_timeout_emitted)

            for idx, tier in enumerate(self.TIERS):
                if elapsed >= tier and idx not in emitted:
                    emitted.add(idx)
                    state.silence_timeout_emitted = sorted(emitted)
                    return idx

        return None
