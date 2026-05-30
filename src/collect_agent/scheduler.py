"""Scheduler — unified heartbeat that scans pending tasks and timeouts.

All time-based triggers go through the scheduled_tasks table (persisted)
rather than in-memory timers or session caches.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from collect_agent.core.constants import EventType
from collect_agent.core.models import Event, ScheduledTask
from collect_agent.session.timeout_tracker import SilenceTimeoutTracker


class OutreachScheduler:
    def __init__(self, system):
        self.system = system
        self.tracker = SilenceTimeoutTracker()

    async def scan_and_outreach(self):
        """Scan all users and trigger outreach for those who need it."""
        states = self.system.store.load_all()
        for state in states:
            # Skip paused users
            if state.paused_until and state.paused_until > datetime.now(UTC):
                continue
            profile = state.profile
            if profile.overdue_days > 0 and state.session_state != "resolved":
                event = Event(
                    user_id=state.user_id,
                    type=EventType.SCHEDULED_OUTREACH,
                )
                await self.system.router.route_async(event)

    async def check_silence_timeouts(self):
        """Check all users for silence timeouts using persisted state."""
        states = self.system.store.load_all()
        for state in states:
            # Skip paused users
            if state.paused_until and state.paused_until > datetime.now(UTC):
                continue

            tier_idx = await self.tracker.check_timeout(state)
            if tier_idx is not None:
                event = Event(
                    user_id=state.user_id,
                    type=EventType.SILENCE_TIMEOUT,
                    payload={
                        "tier": tier_idx,
                        "seconds": SilenceTimeoutTracker.TIERS[tier_idx],
                    },
                )
                await self.system.router.route_async(event)
                # Save updated silence_timeout_emitted
                self.system.store.save(state)

    async def check_scheduled_tasks(self):
        """Execute pending scheduled tasks from the task queue."""
        tasks = self.system.store.load_pending_tasks(before=datetime.now())
        for task in tasks:
            await self._execute_task(task)

    async def _execute_task(self, task: ScheduledTask) -> None:
        """Route a scheduled task as an event and mark it done."""
        if task.task_type == "payment_follow_up":
            event = Event(
                user_id=task.user_id,
                type=EventType.PAYMENT_FOLLOW_UP,
                payload=task.payload,
            )
        elif task.task_type == "reminder":
            event = Event(
                user_id=task.user_id,
                type=EventType.REMINDER_DUE,
                payload=task.payload,
            )
        elif task.task_type == "silence_timeout":
            event = Event(
                user_id=task.user_id,
                type=EventType.SILENCE_TIMEOUT,
                payload=task.payload,
            )
        else:
            # Unknown task type — skip
            return

        await self.system.router.route_async(event)
        self.system.store.complete_task(task.task_id)

    async def run_heartbeat(self, interval_seconds: int = 600) -> None:
        """Background loop: wake up periodically to scan and execute pending work.

        This replaces all ad-hoc polling with a single unified heartbeat.
        """
        while True:
            await asyncio.sleep(interval_seconds)
            await self.scan_and_outreach()
            await self.check_silence_timeouts()
            await self.check_scheduled_tasks()
