"""财务指标同步 HTTP 接口测试：mock handler，验证 endpoint 路由与响应格式。"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.modules.data_engineering.application.commands.sync_finance_indicator_commands import (
    SyncFinanceIndicatorResult,
)
from app.modules.data_engineering.interfaces.dependencies import (
    get_sync_finance_indicator_by_stock_handler,
    get_sync_finance_indicator_full_handler,
    get_sync_finance_indicator_increment_handler,
)

_R = SyncFinanceIndicatorResult(total=10, success_count=9, failure_count=1, synced_records=360)
_RS = SyncFinanceIndicatorResult(total=1, success_count=1, failure_count=0, synced_records=40)


@pytest.fixture
def app_with_mocks():
    from app.interfaces.main import app

    full_handler = AsyncMock()
    full_handler.handle.return_value = _R
    by_stock_handler = AsyncMock()
    by_stock_handler.handle.return_value = _RS
    increment_handler = AsyncMock()
    increment_handler.handle.return_value = _R

    app.dependency_overrides[get_sync_finance_indicator_full_handler] = lambda: full_handler
    app.dependency_overrides[get_sync_finance_indicator_by_stock_handler] = lambda: by_stock_handler
    app.dependency_overrides[get_sync_finance_indicator_increment_handler] = lambda: increment_handler
    yield app
    app.dependency_overrides.pop(get_sync_finance_indicator_full_handler, None)
    app.dependency_overrides.pop(get_sync_finance_indicator_by_stock_handler, None)
    app.dependency_overrides.pop(get_sync_finance_indicator_increment_handler, None)


@pytest.mark.asyncio
async def test_sync_full(app_with_mocks):
    async with AsyncClient(transport=ASGITransport(app=app_with_mocks), base_url="http://test") as c:
        r = await c.post("/api/v1/data-engineering/finance-indicator/sync/full")
    assert r.status_code == 200
    assert r.json()["success_count"] == 9


@pytest.mark.asyncio
async def test_sync_by_stock(app_with_mocks):
    async with AsyncClient(transport=ASGITransport(app=app_with_mocks), base_url="http://test") as c:
        r = await c.post("/api/v1/data-engineering/finance-indicator/sync/by-stock/000001.SZ")
    assert r.status_code == 200
    assert r.json()["synced_records"] == 40


@pytest.mark.asyncio
async def test_sync_increment(app_with_mocks):
    async with AsyncClient(transport=ASGITransport(app=app_with_mocks), base_url="http://test") as c:
        r = await c.post("/api/v1/data-engineering/finance-indicator/sync/increment")
    assert r.status_code == 200
    assert r.json()["total"] == 10
