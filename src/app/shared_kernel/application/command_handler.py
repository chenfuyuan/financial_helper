from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from .command import Command

C = TypeVar("C", bound=Command)
R = TypeVar("R")


class CommandHandler(ABC, Generic[C, R]):
    @abstractmethod
    async def handle(self, command: C) -> R:
        pass
