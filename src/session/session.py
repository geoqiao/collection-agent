from src.core.constants import SessionState
from src.core.models import UserState
from src.session.state_machine import SessionStateMachine
from src.channels.registry import ChannelRegistry
from src.orchestrator.lock import InteractionLock


class CollectionSession:
    def __init__(self, user_id: str, state: UserState):
        self.user_id = user_id
        self.state = state
        self.state_machine = SessionStateMachine()
        self.channels = ChannelRegistry()
        self.lock = InteractionLock()
        self.context = {}

    def handle_event(self, event) -> None:
        pass
