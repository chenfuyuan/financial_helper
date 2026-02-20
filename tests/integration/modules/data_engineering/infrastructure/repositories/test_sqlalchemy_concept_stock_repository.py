from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.modules.data_engineering.domain.entities.concept import Concept
from app.modules.data_engineering.domain.entities.concept_stock import ConceptStock
from app.modules.data_engineering.domain.value_objects.data_source import DataSource
from app.modules.data_engineering.infrastructure.repositories.sqlalchemy_concept_repository import (
    SqlAlchemyConceptRepository,
)
from app.modules.data_engineering.infrastructure.repositories.sqlalchemy_concept_stock_repository import (
    SqlAlchemyConceptStockRepository,
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


async def _seed_concept(session: AsyncSession) -> int:
    repo = SqlAlchemyConceptRepository(session)
    concept = Concept(
        id=None,
        source=DataSource.AKSHARE,
        third_code="BK0818",
        name="人工智能",
        content_hash=Concept.compute_hash(DataSource.AKSHARE, "BK0818", "人工智能"),
        last_synced_at=datetime.now(UTC),
    )
    saved = await repo.save(concept)
    await session.flush()
    return saved.id or -1


def _make_concept_stock(concept_id: int, stock_code: str = "000001") -> ConceptStock:
    return ConceptStock(
        id=None,
        concept_id=concept_id,
        source=DataSource.AKSHARE,
        stock_third_code=stock_code,
        stock_symbol=f"{stock_code}.SZ",
        content_hash=ConceptStock.compute_hash(DataSource.AKSHARE, stock_code, f"{stock_code}.SZ"),
        added_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_save_many_and_find_by_concept_id(engine_and_session) -> None:
    _engine, session_factory = engine_and_session
    async with session_factory() as session:
        concept_id = await _seed_concept(session)
        repo = SqlAlchemyConceptStockRepository(session)
        await repo.save_many(
            [_make_concept_stock(concept_id, "000001"), _make_concept_stock(concept_id, "000002")]
        )
        await session.commit()

    async with session_factory() as session:
        repo = SqlAlchemyConceptStockRepository(session)
        rows = await repo.find_by_concept_id(concept_id)

    assert len(rows) == 2


@pytest.mark.asyncio
async def test_delete_many_removes_rows(engine_and_session) -> None:
    _engine, session_factory = engine_and_session
    async with session_factory() as session:
        concept_id = await _seed_concept(session)
        repo = SqlAlchemyConceptStockRepository(session)
        await repo.save_many(
            [_make_concept_stock(concept_id, "000001"), _make_concept_stock(concept_id, "000002")]
        )
        await session.flush()
        rows = await repo.find_by_concept_id(concept_id)
        await repo.delete_many([row.id for row in rows if row.id is not None])
        await session.commit()

    async with session_factory() as session:
        repo = SqlAlchemyConceptStockRepository(session)
        rows_after = await repo.find_by_concept_id(concept_id)

    assert rows_after == []


@pytest.mark.asyncio
async def test_delete_by_concept_id_removes_all_rows(engine_and_session) -> None:
    _engine, session_factory = engine_and_session
    async with session_factory() as session:
        concept_id = await _seed_concept(session)
        repo = SqlAlchemyConceptStockRepository(session)
        await repo.save_many(
            [_make_concept_stock(concept_id, "000001"), _make_concept_stock(concept_id, "000002")]
        )
        await session.flush()
        await repo.delete_by_concept_id(concept_id)
        await session.commit()

    async with session_factory() as session:
        repo = SqlAlchemyConceptStockRepository(session)
        rows_after = await repo.find_by_concept_id(concept_id)

    assert rows_after == []
