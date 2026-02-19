from dataclasses import dataclass

from app.shared_kernel.domain.aggregate_root import AggregateRoot
from app.shared_kernel.domain.domain_event import DomainEvent


@dataclass(frozen=True)
class ThingCreated(DomainEvent):
    thing_id: int = 0


@dataclass(eq=False)
class Thing(AggregateRoot[int]):
    name: str = ""

    @classmethod
    def create(cls, id: int, name: str) -> "Thing":
        thing = cls(id=id, name=name)
        thing.add_event(ThingCreated(thing_id=id))
        return thing


class TestAggregateRoot:
    def test_is_entity(self) -> None:
        thing = Thing(id=1, name="test")
        assert thing.id == 1

    def test_add_and_collect_events(self) -> None:
        thing = Thing.create(id=1, name="test")
        events = thing.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], ThingCreated)
        assert events[0].thing_id == 1

    def test_collect_events_clears_list(self) -> None:
        thing = Thing.create(id=1, name="test")
        thing.collect_events()
        assert thing.collect_events() == []

    def test_no_events_initially(self) -> None:
        thing = Thing(id=1, name="test")
        assert thing.collect_events() == []

    def test_multiple_events(self) -> None:
        thing = Thing(id=1, name="test")
        thing.add_event(ThingCreated(thing_id=1))
        thing.add_event(ThingCreated(thing_id=1))
        events = thing.collect_events()
        assert len(events) == 2
