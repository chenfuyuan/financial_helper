from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from .aggregate_root import AggregateRoot

AR = TypeVar("AR", bound=AggregateRoot)
ID = TypeVar("ID")


class Repository(ABC, Generic[AR, ID]):
    @abstractmethod
    async def find_by_id(self, id: ID) -> AR | None:
        pass

    @abstractmethod
    async def save(self, aggregate: AR) -> None:
        pass

    @abstractmethod
    async def delete(self, aggregate: AR) -> None:
        pass
