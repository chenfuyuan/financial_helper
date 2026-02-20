"""API Router and Dependencies 注册集成测试。"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.interfaces.main import app
from app.modules.data_engineering.application.commands.sync_stock_daily_history import (
    SyncHistoryResult,
)
from app.modules.data_engineering.application.commands.sync_stock_daily_increment import (
    RetryResult,
    SyncIncrementResult,
)
from app.modules.data_engineering.interfaces.dependencies import (
    get_retry_stock_daily_sync_failures_handler,
    get_sync_stock_daily_history_handler,
    get_sync_stock_daily_increment_handler,
)


@pytest.fixture
def mock_history_handler(mocker):
    handler = mocker.AsyncMock()
    handler.handle.return_value = SyncHistoryResult(total=10, success_count=9, failure_count=1, synced_days=100)
    return handler


@pytest.fixture
def mock_increment_handler(mocker):
    handler = mocker.AsyncMock()
    from datetime import date

    handler.handle.return_value = SyncIncrementResult(trade_date=date(2026, 2, 20), synced_count=5000)
    return handler


@pytest.fixture
def mock_retry_handler(mocker):
    handler = mocker.AsyncMock()
    handler.handle.return_value = RetryResult(total=5, resolved_count=4, still_failed_count=1)
    return handler


@pytest.mark.asyncio
async def test_sync_history_api(mock_history_handler):
    app.dependency_overrides[get_sync_stock_daily_history_handler] = lambda: mock_history_handler
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/data-engineering/stock-daily/sync/history",
                json={"ts_codes": ["000001.SZ"]},
            )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total"] == 10
        assert data["success_count"] == 9
        assert data["failure_count"] == 1
        assert data["synced_days"] == 100
        assert "duration_ms" in data
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_sync_increment_api(mock_increment_handler):
    app.dependency_overrides[get_sync_stock_daily_increment_handler] = lambda: mock_increment_handler
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/data-engineering/stock-daily/sync/increment",
                json={"trade_date": "2026-02-20"},
            )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["trade_date"] == "2026-02-20"
        assert data["synced_count"] == 5000
        assert "duration_ms" in data
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_retry_failures_api(mock_retry_handler):
    app.dependency_overrides[get_retry_stock_daily_sync_failures_handler] = lambda: mock_retry_handler
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/data-engineering/stock-daily/sync/retry-failures",
                json={"max_retries": 5},
            )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["total"] == 5
        assert data["resolved_count"] == 4
        assert data["still_failed_count"] == 1
        assert "duration_ms" in data
    finally:
        app.dependency_overrides.clear()
