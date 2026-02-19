from abc import ABC
from dataclasses import dataclass


@dataclass(frozen=True, eq=True)
class ValueObject(ABC):
    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        pass
