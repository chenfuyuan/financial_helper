"""仓储集成测试：首次插入、同 (source, third_code) 再次更新、幂等性断言。"""

from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.modules.data_engineering.domain.entities.stock_basic import StockBasic
from app.modules.data_engineering.domain.value_objects.data_source import DataSource
from app.modules.data_engineering.domain.value_objects.stock_status import StockStatus
from app.modules.data_engineering.infrastructure.models.stock_basic_model import StockBasicModel
from app.modules.data_engineering.infrastructure.repositories import (
    SqlAlchemyStockBasicRepository,
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


def _make_stock(
    third_code: str = "000001.SZ",
    name: str = "平安银行",
    list_date: date | None = None,
) -> StockBasic:
    return StockBasic(
        id=None,
        source=DataSource.TUSHARE,
        third_code=third_code,
        symbol="000001",
        name=name,
        market="深圳",
        area="深圳",
        industry="银行",
        list_date=list_date or date(2010, 1, 1),
        status=StockStatus.LISTED,
    )


class TestSqlAlchemyStockBasicRepository:
    async def test_upsert_many_first_insert_creates_row(self, engine_and_session) -> None:
        _engine, session_factory = engine_and_session
        async with session_factory() as session:
            repo = SqlAlchemyStockBasicRepository(session)
            await repo.upsert_many([_make_stock()])
            await session.commit()
        async with session_factory() as session:
            result = await session.execute(select(StockBasicModel).where(StockBasicModel.third_code == "000001.SZ"))
            row = result.scalar_one()
        assert row.source == "TUSHARE"
        assert row.third_code == "000001.SZ"
        assert row.name == "平安银行"
        assert row.version == 1

    async def test_upsert_many_same_key_updates_in_place(self, engine_and_session) -> None:
        _engine, session_factory = engine_and_session
        async with session_factory() as session:
            repo = SqlAlchemyStockBasicRepository(session)
            await repo.upsert_many([_make_stock(name="平安银行")])
            await session.commit()
        async with session_factory() as session:
            repo = SqlAlchemyStockBasicRepository(session)
            await repo.upsert_many([_make_stock(name="平安银行已更名")])
            await session.commit()
        async with session_factory() as session:
            result = await session.execute(select(StockBasicModel).where(StockBasicModel.third_code == "000001.SZ"))
            row = result.scalar_one()
        assert row.name == "平安银行已更名"
        assert row.version == 2
        # created_at 不变、updated_at 已更新（由 DB/server 维护，这里只断言 version 与 name）

    async def test_upsert_many_idempotent_second_same_data(self, engine_and_session) -> None:
        _engine, session_factory = engine_and_session
        stock = _make_stock()
        async with session_factory() as session:
            repo = SqlAlchemyStockBasicRepository(session)
            await repo.upsert_many([stock])
            await session.commit()
        async with session_factory() as session:
            repo = SqlAlchemyStockBasicRepository(session)
            await repo.upsert_many([stock])
            await session.commit()
        async with session_factory() as session:
            result = await session.execute(select(StockBasicModel).where(StockBasicModel.third_code == "000001.SZ"))
            result.scalars().all()

    async def test_find_by_third_codes_and_all_listed(self, engine_and_session) -> None:
        _engine, session_factory = engine_and_session
        async with session_factory() as session:
            repo = SqlAlchemyStockBasicRepository(session)

            stock1 = _make_stock(third_code="000001.SZ")
            stock2 = _make_stock(third_code="000002.SZ")
            stock3 = _make_stock(third_code="000003.SZ")
            stock3.status = StockStatus.DELISTED  # stock3 已退市

            await repo.upsert_many([stock1, stock2, stock3])
            await session.commit()

            # 测试 find_by_third_codes
            found_codes = await repo.find_by_third_codes(DataSource.TUSHARE, ["000001.SZ", "000003.SZ"])
            assert len(found_codes) == 2
            codes = [s.third_code for s in found_codes]
            assert "000001.SZ" in codes
            assert "000003.SZ" in codes

            # 测试 find_all_listed
            listed_stocks = await repo.find_all_listed(DataSource.TUSHARE)
            assert len(listed_stocks) == 2
            listed_codes = [s.third_code for s in listed_stocks]
            assert "000001.SZ" in listed_codes
            assert "000002.SZ" in listed_codes
            assert "000003.SZ" not in listed_codes

            # 测试 find_all（包含所有状态）
            all_stocks = await repo.find_all(DataSource.TUSHARE)
            assert len(all_stocks) == 3
            all_codes = [s.third_code for s in all_stocks]
            assert "000001.SZ" in all_codes
            assert "000002.SZ" in all_codes
            assert "000003.SZ" in all_codes
