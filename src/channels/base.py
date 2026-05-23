from abc import ABC, abstractmethod
from src.core.constants import ChannelType


class BaseChannel(ABC):
    @property
    @abstractmethod
    def channel_type(self) -> ChannelType:
        pass

    @abstractmethod
    async def send(self, user_id: str, content: str) -> dict:
        pass
