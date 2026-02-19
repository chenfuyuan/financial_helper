"""SyncStockBasicHandler 单测：fake 网关与仓储，验证编排与异常上抛。"""

from datetime import date, datetime
from unittest.mock import AsyncMock

import pytest

from app.modules.data_engineering.application.commands.sync_stock_basic import SyncStockBasic
from app.modules.data_engineering.application.commands.sync_stock_basic_handler import (
    SyncStockBasicHandler,
)
from app.modules.data_engineering.domain.entities.stock_basic import (
    DataSource,
    StockBasic,
    StockStatus,
)


def _make_stock(third_code: str = "000001.SZ", name: str = "平安银行") -> StockBasic:
    return StockBasic(
        id=None,
        created_at=datetime(2020, 1, 1),
        updated_at=datetime(2020, 1, 1),
        version=0,
        source=DataSource.TUSHARE,
        third_code=third_code,
        symbol="000001",
        name=name,
        market="深圳",
        area="深圳",
        industry="银行",
        list_date=date(2010, 1, 1),
        status=StockStatus.LISTED,
    )


class TestSyncStockBasicHandler:
    @pytest.mark.asyncio
    async def test_handle_calls_gateway_then_upsert_many_returns_count(self) -> None:
        stocks = [_make_stock(), _make_stock("000002.SZ", "万科A")]
        gateway = AsyncMock()
        gateway.fetch_stock_basic = AsyncMock(return_value=stocks)
        repo = AsyncMock()
        repo.upsert_many = AsyncMock(return_value=None)
        handler = SyncStockBasicHandler(gateway=gateway, repository=repo)
        result = await handler.handle(SyncStockBasic())
        assert result == 2
        gateway.fetch_stock_basic.assert_awaited_once()
        repo.upsert_many.assert_awaited_once_with(stocks)

    @pytest.mark.asyncio
    async def test_handle_when_gateway_raises_propagates_and_no_upsert(self) -> None:
        gateway = AsyncMock()
        gateway.fetch_stock_basic = AsyncMock(side_effect=Exception("network error"))
        repo = AsyncMock()
        repo.upsert_many = AsyncMock(return_value=None)
        handler = SyncStockBasicHandler(gateway=gateway, repository=repo)
        with pytest.raises(Exception, match="network error"):
            await handler.handle(SyncStockBasic())
        repo.upsert_many.assert_not_called()
