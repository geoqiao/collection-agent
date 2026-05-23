from src.core.models import UserState


class MemoryStore:
    def __init__(self):
        self._data: dict[str, UserState] = {}

    def save(self, state: UserState) -> None:
        self._data[state.user_id] = state

    def load(self, user_id: str) -> UserState | None:
        return self._data.get(user_id)

    def load_all(self) -> list[UserState]:
        return list(self._data.values())

    def delete(self, user_id: str) -> None:
        self._data.pop(user_id, None)
