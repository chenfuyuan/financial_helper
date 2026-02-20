from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.modules.data_engineering.domain.entities.concept import Concept
from app.modules.data_engineering.domain.value_objects.data_source import DataSource
from app.modules.data_engineering.infrastructure.repositories.sqlalchemy_concept_repository import (
    SqlAlchemyConceptRepository,
)
from app.shared_kernel.infrastructure.database import Base


@pytest.fixture
async def engine_and_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield engine, factory
    await engine.dispose()


def _make_concept(third_code: str = "BK0818", name: str = "人工智能") -> Concept:
    return Concept(
        id=None,
        source=DataSource.AKSHARE,
        third_code=third_code,
        name=name,
        content_hash=Concept.compute_hash(DataSource.AKSHARE, third_code, name),
        last_synced_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_save_and_find_by_third_code(engine_and_session) -> None:
    _engine, session_factory = engine_and_session
    async with session_factory() as session:
        repo = SqlAlchemyConceptRepository(session)
        saved = await repo.save(_make_concept())
        await session.commit()

    async with session_factory() as session:
        repo = SqlAlchemyConceptRepository(session)
        found = await repo.find_by_third_code(DataSource.AKSHARE, "BK0818")

    assert saved.id is not None
    assert found is not None
    assert found.name == "人工智能"


@pytest.mark.asyncio
async def test_save_updates_existing_record(engine_and_session) -> None:
    _engine, session_factory = engine_and_session
    async with session_factory() as session:
        repo = SqlAlchemyConceptRepository(session)
        await repo.save(_make_concept(name="人工智能"))
        await session.commit()

    async with session_factory() as session:
        repo = SqlAlchemyConceptRepository(session)
        updated = await repo.save(_make_concept(name="AI概念"))
        await session.commit()

    assert updated.name == "AI概念"
    assert updated.id is not None


@pytest.mark.asyncio
async def test_find_all_and_delete(engine_and_session) -> None:
    _engine, session_factory = engine_and_session
    async with session_factory() as session:
        repo = SqlAlchemyConceptRepository(session)
        c1 = await repo.save(_make_concept(third_code="BK0001", name="A"))
        await repo.save(_make_concept(third_code="BK0002", name="B"))
        await session.commit()

    async with session_factory() as session:
        repo = SqlAlchemyConceptRepository(session)
        all_concepts = await repo.find_all(DataSource.AKSHARE)
        await repo.delete(c1.id or -1)
        await session.commit()
        after_delete = await repo.find_all(DataSource.AKSHARE)

    assert len(all_concepts) == 2
    assert len(after_delete) == 1
