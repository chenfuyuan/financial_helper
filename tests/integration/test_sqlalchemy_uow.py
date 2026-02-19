import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.shared_kernel.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


@pytest.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield factory
    await engine.dispose()


class TestSqlAlchemyUnitOfWork:
    async def test_provides_session(self, session_factory) -> None:
        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            assert uow.session is not None

    async def test_commit(self, session_factory) -> None:
        async with SqlAlchemyUnitOfWork(session_factory) as uow:
            await uow.commit()

    async def test_rollback_on_exception(self, session_factory) -> None:
        with pytest.raises(ValueError):
            async with SqlAlchemyUnitOfWork(session_factory) as _:
                raise ValueError("boom")
