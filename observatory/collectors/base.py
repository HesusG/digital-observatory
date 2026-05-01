from abc import ABC, abstractmethod

from observatory.storage.models import CollectedItem


class BaseCollector(ABC):
    name: str = "base"
    source_type: str = "unknown"

    @abstractmethod
    async def collect(self) -> list[CollectedItem]:
        ...
