import asyncio
import logging

from collect_agent.core.models import Event

logger = logging.getLogger(__name__)


class EventRouter:
    def __init__(self, session_manager):
        self.session_manager = session_manager

    async def route_async(self, event: Event) -> None:
        session = self.session_manager.get_or_create(event.user_id)
        if asyncio.iscoroutinefunction(session.handle_event):
            await session.handle_event(event)
        else:
            session.handle_event(event)

    def _on_task_done(self, task) -> None:
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:
            logger.exception("Event routing failed: %s", exc)

    def route(self, event: Event) -> None:
        """Synchronous wrapper - for sync contexts"""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # No loop running - use asyncio.run
            asyncio.run(self.route_async(event))
        else:
            # Already in async context - schedule as task with exception handling
            task = asyncio.create_task(self.route_async(event))
            task.add_done_callback(self._on_task_done)
