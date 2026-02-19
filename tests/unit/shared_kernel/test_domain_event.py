from dataclasses import dataclass
from datetime import UTC, datetime

from app.shared_kernel.domain.domain_event import DomainEvent


@dataclass(frozen=True)
class FakeEvent(DomainEvent):
    entity_id: int = 0


class TestDomainEvent:
    def test_has_occurred_at(self) -> None:
        event = FakeEvent(entity_id=42)
        assert isinstance(event.occurred_at, datetime)

    def test_is_immutable(self) -> None:
        event = FakeEvent(entity_id=42)
        try:
            event.entity_id = 99  # type: ignore[misc]
            raise AssertionError("Should raise FrozenInstanceError")
        except AttributeError:
            pass

    def test_equality_by_value(self) -> None:
        ts = datetime.now(UTC)
        a = FakeEvent(entity_id=1, occurred_at=ts)
        b = FakeEvent(entity_id=1, occurred_at=ts)
        assert a == b
