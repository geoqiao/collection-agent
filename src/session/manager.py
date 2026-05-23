from src.session.session import CollectionSession
from src.core.models import UserState, UserProfile
from src.storage.memory_store import MemoryStore


class SessionManager:
    def __init__(self, store: MemoryStore | None = None):
        self._store = store or MemoryStore()
        self._sessions: dict[str, CollectionSession] = {}

    def get_or_create(self, user_id: str) -> CollectionSession:
        if user_id in self._sessions:
            return self._sessions[user_id]

        state = self._store.load(user_id)
        if state is None:
            state = UserState(
                user_id=user_id,
                profile=UserProfile(user_id=user_id),
            )
            self._store.save(state)

        session = CollectionSession(user_id=user_id, state=state)
        self._sessions[user_id] = session
        return session

    def get(self, user_id: str) -> CollectionSession | None:
        return self._sessions.get(user_id)

    def remove(self, user_id: str) -> None:
        if user_id in self._sessions:
            session = self._sessions[user_id]
            self._store.save(session.state)
            del self._sessions[user_id]
