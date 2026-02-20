from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.data_engineering.application.commands.sync_stock_daily_history import (
    SyncStockDailyHistory,
)
from app.modules.data_engineering.application.commands.sync_stock_daily_history_handler import (
    SyncStockDailyHistoryHandler,
)
from app.modules.data_engineering.domain.entities.stock_basic import StockBasic
from app.modules.data_engineering.domain.value_objects.data_source import DataSource
from app.modules.data_engineering.domain.value_objects.stock_status import StockStatus


@pytest.fixture
def mock_gateway():
    return AsyncMock()


@pytest.fixture
def mock_daily_repo():
    repo = AsyncMock()
    # 默认没找到最新日期
    repo.get_latest_trade_date.return_value = None
    return repo


@pytest.fixture
def mock_basic_repo():
    repo = AsyncMock()
    return repo


@pytest.fixture
def mock_failure_repo():
    return AsyncMock()


@pytest.fixture
def mock_uow():
    uow = AsyncMock()
    return uow


@pytest.fixture
def handler(mock_gateway, mock_daily_repo, mock_basic_repo, mock_failure_repo, mock_uow):
    return SyncStockDailyHistoryHandler(
        gateway=mock_gateway,
        daily_repo=mock_daily_repo,
        basic_repo=mock_basic_repo,
        failure_repo=mock_failure_repo,
        uow=mock_uow,
    )


def _make_stock(ts_code: str, list_date: date) -> StockBasic:
    return StockBasic(
        id=1,
        source=DataSource.TUSHARE,
        third_code=ts_code,
        symbol=ts_code.split(".")[0],
        name="Test",
        market="Test",
        area="Test",
        industry="Test",
        list_date=list_date,
        status=StockStatus.LISTED,
    )


@pytest.mark.asyncio
@patch("app.modules.data_engineering.application.commands.sync_stock_daily_history_handler.date")
async def test_history_sync_first_time(mock_date, handler, mock_basic_repo, mock_gateway):
    """测试首次同步：无最新日期，从上市日期同步到今天"""
    mock_date.today.return_value = date(2026, 2, 20)

    mock_basic_repo.find_by_third_codes.return_value = [_make_stock("000001.SZ", date(2026, 2, 18))]
    mock_gateway.fetch_stock_daily.return_value = [MagicMock()]

    cmd = SyncStockDailyHistory(ts_codes=["000001.SZ"])
    res = await handler.handle(cmd)

    assert res.total == 1
    assert res.success_count == 1
    assert res.failure_count == 0

    mock_gateway.fetch_stock_daily.assert_called_once_with("000001.SZ", date(2026, 2, 18), date(2026, 2, 20))
    handler.uow.commit.assert_called_once()
