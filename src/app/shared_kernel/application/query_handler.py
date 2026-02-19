from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from .query import Query

Q = TypeVar("Q", bound=Query)
R = TypeVar("R")


class QueryHandler(ABC, Generic[Q, R]):
    @abstractmethod
    async def handle(self, query: Q) -> R:
        pass
