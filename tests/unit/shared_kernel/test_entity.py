from dataclasses import dataclass

from app.shared_kernel.domain.entity import Entity


@dataclass(eq=False)
class FakeEntity(Entity[int]):
    name: str = ""


class TestEntity:
    def test_equal_by_id(self) -> None:
        a = FakeEntity(id=1, name="Alice")
        b = FakeEntity(id=1, name="Bob")
        assert a == b

    def test_not_equal_different_id(self) -> None:
        a = FakeEntity(id=1)
        b = FakeEntity(id=2)
        assert a != b

    def test_not_equal_different_type(self) -> None:
        @dataclass(eq=False)
        class OtherEntity(Entity[int]):
            pass

        a = FakeEntity(id=1)
        b = OtherEntity(id=1)
        assert a != b

    def test_hash_by_type_and_id(self) -> None:
        a = FakeEntity(id=1, name="Alice")
        b = FakeEntity(id=1, name="Bob")
        assert hash(a) == hash(b)
        assert len({a, b}) == 1

    def test_not_equal_to_non_entity(self) -> None:
        a = FakeEntity(id=1)
        assert a != "not an entity"
        assert a != 1
        assert a != None  # noqa: E711
