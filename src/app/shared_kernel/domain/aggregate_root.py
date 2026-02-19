from abc import ABC
from dataclasses import dataclass, field

from .domain_event import DomainEvent
from .entity import ID, Entity


@dataclass(eq=False)
class AggregateRoot(Entity[ID], ABC):
    _events: list[DomainEvent] = field(default_factory=list, init=False, repr=False)

    def add_event(self, event: DomainEvent) -> None:
        self._events.append(event)

    def collect_events(self) -> list[DomainEvent]:
        events = self._events.copy()
        self._events.clear()
        return events
