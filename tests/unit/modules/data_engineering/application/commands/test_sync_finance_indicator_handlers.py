from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.data_engineering.application.commands.sync_finance_indicator_commands import (
    SyncFinanceIndicatorByStock,
    SyncFinanceIndicatorFull,
    SyncFinanceIndicatorIncrement,
)
from app.modules.data_engineering.application.commands.sync_finance_indicator_by_stock_handler import (
    SyncFinanceIndicatorByStockHandler,
)
from app.modules.data_engineering.application.commands.sync_finance_indicator_full_handler import (
    SyncFinanceIndicatorFullHandler,
)
from app.modules.data_engineering.application.commands.sync_finance_indicator_increment_handler import (
    SyncFinanceIndicatorIncrementHandler,
)
from app.modules.data_engineering.domain.value_objects.data_source import DataSource


def _uow():
    u = AsyncMock()
    u.__aenter__ = AsyncMock(return_value=u)
    u.__aexit__ = AsyncMock(return_value=False)
    return u


def _stock(code="000001.SZ"):
    s = MagicMock()
    s.third_code = code
    s.source = DataSource.TUSHARE
    return s


@pytest.mark.asyncio
async def test_full_syncs_all_stocks():
    basic_repo = AsyncMock()
    basic_repo.find_all.return_value = [_stock()]
    fi_repo = AsyncMock()
    gateway = AsyncMock()
    gateway.fetch_by_stock.return_value = [MagicMock()]
    result = await SyncFinanceIndicatorFullHandler(
        basic_repo, fi_repo, gateway, _uow()
    ).handle(SyncFinanceIndicatorFull())
    assert result.total == 1 and result.success_count == 1 and result.failure_count == 0


@pytest.mark.asyncio
async def test_by_stock_returns_count():
    fi_repo = AsyncMock()
    gateway = AsyncMock()
    gateway.fetch_by_stock.return_value = [MagicMock(), MagicMock()]
    result = await SyncFinanceIndicatorByStockHandler(
        fi_repo, gateway, _uow()
    ).handle(SyncFinanceIndicatorByStock(ts_code="000001.SZ"))
    assert result.synced_records == 2


@pytest.mark.asyncio
async def test_increment_uses_latest_end_date():
    basic_repo = AsyncMock()
    basic_repo.find_all_listed.return_value = [_stock()]
    fi_repo = AsyncMock()
    fi_repo.get_latest_end_date.return_value = date(2023, 9, 30)
    gateway = AsyncMock()
    gateway.fetch_by_stock.return_value = []
    await SyncFinanceIndicatorIncrementHandler(
        basic_repo, fi_repo, gateway, _uow()
    ).handle(SyncFinanceIndicatorIncrement())
    gateway.fetch_by_stock.assert_called_once_with("000001.SZ", start_date=date(2023, 10, 1))
