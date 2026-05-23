from src.core.models import Event


class EventRouter:
    def __init__(self, session_manager):
        self.session_manager = session_manager

    def route(self, event: Event) -> None:
        session = self.session_manager.get_or_create(event.user_id)
        session.handle_event(event)
