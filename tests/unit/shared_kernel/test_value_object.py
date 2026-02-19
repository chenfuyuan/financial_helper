from dataclasses import dataclass

import pytest

from app.shared_kernel.domain.exception import ValidationException
from app.shared_kernel.domain.value_object import ValueObject


@dataclass(frozen=True)
class Email(ValueObject):
    address: str = ""

    def _validate(self) -> None:
        if self.address and "@" not in self.address:
            raise ValidationException(f"Invalid email: {self.address}")


class TestValueObject:
    def test_is_immutable(self) -> None:
        vo = Email(address="a@b.com")
        with pytest.raises(AttributeError):
            vo.address = "x@y.com"  # type: ignore[misc]

    def test_equality_by_value(self) -> None:
        a = Email(address="a@b.com")
        b = Email(address="a@b.com")
        assert a == b

    def test_inequality_by_value(self) -> None:
        a = Email(address="a@b.com")
        b = Email(address="x@y.com")
        assert a != b

    def test_validation_hook_called(self) -> None:
        with pytest.raises(ValidationException, match="Invalid email"):
            Email(address="not-an-email")

    def test_validation_hook_passes(self) -> None:
        email = Email(address="valid@test.com")
        assert email.address == "valid@test.com"
