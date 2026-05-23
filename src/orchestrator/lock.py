from datetime import datetime
from src.core.constants import ChannelType


class InteractionLock:
    def __init__(self):
        self._holder: ChannelType | None = None
        self._acquired_at: datetime | None = None

    @property
    def holder(self) -> ChannelType | None:
        return self._holder

    @property
    def is_locked(self) -> bool:
        return self._holder is not None

    def acquire(self, channel: ChannelType) -> None:
        self._holder = channel
        self._acquired_at = datetime.now()

    def release(self) -> None:
        self._holder = None
        self._acquired_at = None
