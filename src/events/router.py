import asyncio

from src.core.models import Event


class EventRouter:
    def __init__(self, session_manager):
        self.session_manager = session_manager

    async def route_async(self, event: Event) -> None:
        session = self.session_manager.get_or_create(event.user_id)
        if asyncio.iscoroutinefunction(session.handle_event):
            await session.handle_event(event)
        else:
            session.handle_event(event)

    def route(self, event: Event) -> None:
        """Synchronous wrapper - for sync contexts"""
        try:
            asyncio.get_running_loop()
            # Already in async context - schedule as task
            asyncio.create_task(self.route_async(event))
        except RuntimeError:
            # No loop running - use asyncio.run
            asyncio.run(self.route_async(event))
