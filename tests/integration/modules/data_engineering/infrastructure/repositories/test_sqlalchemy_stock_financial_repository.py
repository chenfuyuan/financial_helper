from dataclasses import fields as dc_fields
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.modules.data_engineering.domain.entities.stock_financial import StockFinancial
from app.modules.data_engineering.domain.value_objects.data_source import DataSource
from app.modules.data_engineering.infrastructure.repositories.sqlalchemy_stock_financial_repository import (
    SqlAlchemyStockFinancialRepository,
)
from app.shared_kernel.infrastructure.database import Base

_FIXED = {"id", "source", "third_code", "symbol", "end_date"}


@pytest.fixture
async def engine_and_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield engine, factory
    await engine.dispose()


def _make(third_code="000001.SZ", end_date=date(2023, 12, 31), **kwargs) -> StockFinancial:
    base = {
        "id": None,
        "source": DataSource.TUSHARE,
        "third_code": third_code,
        "symbol": None,
        "end_date": end_date,
        **{f.name: None for f in dc_fields(StockFinancial) if f.name not in _FIXED},
    }
    base.update(kwargs)
    return StockFinancial(**base)


@pytest.mark.asyncio
async def test_upsert_many_and_get_latest_end_date(engine_and_session):
    _engine, session_factory = engine_and_session
    async with session_factory() as db_session:
        repo = SqlAlchemyStockFinancialRepository(db_session)
        records = [
            _make(end_date=date(2023, 3, 31), eps=Decimal("1.0")),
            _make(end_date=date(2023, 12, 31), eps=Decimal("2.0")),
        ]
        await repo.upsert_many(records)
        await db_session.commit()

        latest = await repo.get_latest_end_date(DataSource.TUSHARE, "000001.SZ")
        assert latest == date(2023, 12, 31)


@pytest.mark.asyncio
async def test_upsert_many_is_idempotent(engine_and_session):
    _engine, session_factory = engine_and_session
    async with session_factory() as db_session:
        repo = SqlAlchemyStockFinancialRepository(db_session)
        record = _make(end_date=date(2023, 12, 31), eps=Decimal("1.0"))
        await repo.upsert_many([record])
        await db_session.commit()
        updated = _make(end_date=date(2023, 12, 31), eps=Decimal("9.9"))
        await repo.upsert_many([updated])
        await db_session.commit()

        latest = await repo.get_latest_end_date(DataSource.TUSHARE, "000001.SZ")
        assert latest == date(2023, 12, 31)


@pytest.mark.asyncio
async def test_get_latest_end_date_no_records(engine_and_session):
    _engine, session_factory = engine_and_session
    async with session_factory() as db_session:
        repo = SqlAlchemyStockFinancialRepository(db_session)
        result = await repo.get_latest_end_date(DataSource.TUSHARE, "999999.SZ")
        assert result is None
