from abc import ABC
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

ID = TypeVar("ID", bound=Any)


@dataclass(eq=False)
class Entity(ABC, Generic[ID]):
    id: ID

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return False
        return bool(self.id == other.id)

    def __hash__(self) -> int:
        return hash((type(self), self.id))
