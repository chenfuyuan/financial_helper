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
async def test_save_many_creates_and_updates(engine_and_session) -> None:
    """测试批量保存：新增和更新操作。"""
    _engine, session_factory = engine_and_session

    # 先保存一个概念用于测试更新
    async with session_factory() as session:
        repo = SqlAlchemyConceptRepository(session)
        existing = await repo.save(_make_concept(third_code="BK0001", name="人工智能"))
        await session.commit()

    # 准备批量数据：包含新增和更新
    concepts_to_save = [
        _make_concept(third_code="BK0001", name="AI概念"),  # 更新现有概念
        _make_concept(third_code="BK0002", name="新能源"),  # 新增概念
        _make_concept(third_code="BK0003", name="生物医药"),  # 新增概念
    ]

    async with session_factory() as session:
        repo = SqlAlchemyConceptRepository(session)
        saved_concepts = await repo.save_many(concepts_to_save)
        await session.commit()

    # 验证结果
    assert len(saved_concepts) == 3
    assert all(c.id is not None for c in saved_concepts)

    # 验证更新操作
    updated_concept = next(c for c in saved_concepts if c.third_code == "BK0001")
    assert updated_concept.name == "AI概念"
    assert updated_concept.id == existing.id  # ID应该保持不变

    # 验证新增操作
    new_concept = next(c for c in saved_concepts if c.third_code == "BK0002")
    assert new_concept.name == "新能源"
    assert new_concept.id is not None

    # 验证数据库中的数据
    async with session_factory() as session:
        repo = SqlAlchemyConceptRepository(session)
        all_concepts = await repo.find_all(DataSource.AKSHARE)

    assert len(all_concepts) == 3
    assert sorted(c.third_code for c in all_concepts) == ["BK0001", "BK0002", "BK0003"]


@pytest.mark.asyncio
async def test_save_many_empty_list(engine_and_session) -> None:
    """测试批量保存空列表。"""
    _engine, session_factory = engine_and_session
    async with session_factory() as session:
        repo = SqlAlchemyConceptRepository(session)
        result = await repo.save_many([])
        await session.commit()

    assert result == []


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
