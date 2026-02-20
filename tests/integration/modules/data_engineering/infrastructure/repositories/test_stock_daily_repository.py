from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.modules.data_engineering.domain.entities.stock_daily import StockDaily
from app.modules.data_engineering.domain.value_objects.data_source import DataSource
from app.modules.data_engineering.infrastructure.repositories.sqlalchemy_stock_daily_repository import (
    SqlAlchemyStockDailyRepository,
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


@pytest.mark.asyncio
async def test_upsert_many_and_get_latest_date(engine_and_session):
    engine, session_factory = engine_and_session
    async with session_factory() as db_session:
        repository = SqlAlchemyStockDailyRepository(db_session)
        
        # 1. 验证空表查 latest
        latest = await repository.get_latest_trade_date(DataSource.TUSHARE, "000001.SZ")
        assert latest is None

        # 2. Insert new
        daily1 = StockDaily(
            id=None,
            source=DataSource.TUSHARE,
            third_code="000001.SZ",
            trade_date=date(2026, 1, 1),
            open=Decimal("10.0"),
            high=Decimal("11.0"),
            low=Decimal("9.0"),
            close=Decimal("10.5"),
            pre_close=Decimal("9.5"),
            change=Decimal("1.0"),
            pct_chg=Decimal("10.0"),
            vol=Decimal("100"),
            amount=Decimal("1000"),
            adj_factor=Decimal("1.5"),
            turnover_rate=None,
            turnover_rate_f=None,
            volume_ratio=None,
            pe=None,
            pe_ttm=None,
            pb=None,
            ps=None,
            ps_ttm=None,
            dv_ratio=None,
            dv_ttm=None,
            total_share=None,
            float_share=None,
            free_share=None,
            total_mv=None,
            circ_mv=None,
        )
        daily2 = StockDaily(
            id=None,
            source=DataSource.TUSHARE,
            third_code="000001.SZ",
            trade_date=date(2026, 1, 2),
            open=Decimal("10.5"),
            high=Decimal("11.5"),
            low=Decimal("9.5"),
            close=Decimal("11.0"),
            pre_close=Decimal("10.5"),
            change=Decimal("0.5"),
            pct_chg=Decimal("5.0"),
            vol=Decimal("150"),
            amount=Decimal("1500"),
            adj_factor=Decimal("1.5"),
            turnover_rate=None,
            turnover_rate_f=None,
            volume_ratio=None,
            pe=None,
            pe_ttm=None,
            pb=None,
            ps=None,
            ps_ttm=None,
            dv_ratio=None,
            dv_ttm=None,
            total_share=None,
            float_share=None,
            free_share=None,
            total_mv=None,
            circ_mv=None,
        )
        await repository.upsert_many([daily1, daily2])
        await db_session.commit()

        latest = await repository.get_latest_trade_date(DataSource.TUSHARE, "000001.SZ")
        assert latest == date(2026, 1, 2)

        # 3. Upsert existing
        daily1_updated = StockDaily(
            id=None,
            source=DataSource.TUSHARE,
            third_code="000001.SZ",
            trade_date=date(2026, 1, 1),
            open=Decimal("100.0"),  # modified
            high=Decimal("11.0"),
            low=Decimal("9.0"),
            close=Decimal("10.5"),
            pre_close=Decimal("9.5"),
            change=Decimal("1.0"),
            pct_chg=Decimal("10.0"),
            vol=Decimal("100"),
            amount=Decimal("1000"),
            adj_factor=Decimal("1.5"),
            turnover_rate=None,
            turnover_rate_f=None,
            volume_ratio=None,
            pe=None,
            pe_ttm=None,
            pb=None,
            ps=None,
            ps_ttm=None,
            dv_ratio=None,
            dv_ttm=None,
            total_share=None,
            float_share=None,
            free_share=None,
            total_mv=None,
            circ_mv=None,
        )
        await repository.upsert_many([daily1_updated])
        await db_session.commit()

