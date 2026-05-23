from src.events.router import EventRouter
from src.session.manager import SessionManager
from src.storage.memory_store import MemoryStore


class CollectAgentSystem:
    def __init__(self):
        self.store = MemoryStore()
        self.session_manager = SessionManager(self.store)
        self.router = EventRouter(self.session_manager)

    def handle_event(self, event) -> None:
        self.router.route(event)

    def get_session(self, user_id: str):
        return self.session_manager.get(user_id)
