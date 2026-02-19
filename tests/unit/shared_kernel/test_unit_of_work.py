import pytest

from app.shared_kernel.domain.unit_of_work import UnitOfWork


class FakeUnitOfWork(UnitOfWork):
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> "FakeUnitOfWork":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore[no-untyped-def]
        if exc_type:
            await self.rollback()

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class TestUnitOfWork:
    async def test_commit(self) -> None:
        async with FakeUnitOfWork() as uow:
            await uow.commit()
        assert uow.committed is True

    async def test_rollback_on_exception(self) -> None:
        uow = FakeUnitOfWork()
        with pytest.raises(ValueError):
            async with uow:
                raise ValueError("boom")
        assert uow.rolled_back is True

    async def test_context_manager_returns_self(self) -> None:
        async with FakeUnitOfWork() as uow:
            assert isinstance(uow, FakeUnitOfWork)
