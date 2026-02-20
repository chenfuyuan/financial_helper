from datetime import date
from unittest.mock import AsyncMock

import pytest

from app.modules.data_engineering.application.commands.retry_stock_daily_sync_failures_handler import (
    RetryStockDailySyncFailuresHandler,
)
from app.modules.data_engineering.application.commands.sync_stock_daily_increment import (
    RetryStockDailySyncFailures,
    SyncStockDailyIncrement,
)
from app.modules.data_engineering.application.commands.sync_stock_daily_increment_handler import (
    SyncStockDailyIncrementHandler,
)
from app.modules.data_engineering.domain.entities.stock_daily_sync_failure import (
    StockDailySyncFailure,
)
from app.modules.data_engineering.domain.value_objects.data_source import DataSource


@pytest.fixture
def mock_gateway():
    return AsyncMock()


@pytest.fixture
def mock_daily_repo():
    return AsyncMock()


@pytest.fixture
def mock_failure_repo():
    return AsyncMock()


@pytest.fixture
def mock_uow():
    uow = AsyncMock()
    return uow


@pytest.mark.asyncio
async def test_increment_sync_success(mock_gateway, mock_daily_repo, mock_uow):
    mock_gateway.fetch_daily_all_by_date.return_value = ["mock_record"]
    handler = SyncStockDailyIncrementHandler(
        gateway=mock_gateway, daily_repo=mock_daily_repo, uow=mock_uow
    )

    cmd = SyncStockDailyIncrement(trade_date=date(2026, 2, 20))
    res = await handler.handle(cmd)

    assert res.trade_date == date(2026, 2, 20)
    assert res.synced_count == 1

    mock_gateway.fetch_daily_all_by_date.assert_called_once_with(date(2026, 2, 20))
    mock_daily_repo.upsert_many.assert_called_once_with(["mock_record"])
    mock_uow.commit.assert_called_once()


@pytest.mark.asyncio
async def test_retry_failures_success_and_failure(
    mock_gateway, mock_daily_repo, mock_failure_repo, mock_uow
):
    failure1 = StockDailySyncFailure(
        id=1,
        source=DataSource.TUSHARE,
        third_code="000001.SZ",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 10),
        error_message="err",
        failed_at=None,
        retry_count=0,
        resolved=False,
    )
    failure2 = StockDailySyncFailure(
        id=2,
        source=DataSource.TUSHARE,
        third_code="000002.SZ",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 10),
        error_message="err",
        failed_at=None,
        retry_count=0,
        resolved=False,
    )
    mock_failure_repo.find_unresolved.return_value = [failure1, failure2]

    # 第一个成功，第二个失败
    mock_gateway.fetch_stock_daily.side_effect = [["mock_record"], Exception("still failing")]

    handler = RetryStockDailySyncFailuresHandler(
        gateway=mock_gateway,
        daily_repo=mock_daily_repo,
        failure_repo=mock_failure_repo,
        uow=mock_uow,
    )

    cmd = RetryStockDailySyncFailures()
    res = await handler.handle(cmd)

    assert res.total == 2
    assert res.resolved_count == 1
    assert res.still_failed_count == 1

    mock_failure_repo.mark_resolved.assert_called_once_with(1)
    mock_failure_repo.save.assert_called_once()
    assert failure2.retry_count == 1
    assert "still failing" in failure2.error_message
