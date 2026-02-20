import asyncio
from datetime import date
from unittest.mock import AsyncMock, patch
import pytest

from app.modules.data_engineering.domain.exceptions import ExternalStockServiceError
from app.modules.data_engineering.infrastructure.gateways.mappers.tushare_stock_daily_mapper import (
    TuShareStockDailyMapper,
)
from app.modules.data_engineering.infrastructure.gateways.tushare_stock_daily_gateway import (
    TuShareStockDailyGateway,
)


@pytest.fixture
def mapper():
    return TuShareStockDailyMapper()


@pytest.fixture
def gateway(mapper):
    return TuShareStockDailyGateway(token="dummy", mapper=mapper)


@pytest.mark.asyncio
@patch("app.modules.data_engineering.infrastructure.gateways.tushare_stock_daily_gateway.asyncio.to_thread")
async def test_fetch_stock_daily_calls_three_apis(mock_to_thread, gateway):
    # 模拟三个接口返回
    mock_to_thread.side_effect = [
        [{"ts_code": "000001.SZ", "trade_date": "20260220", "open": "10", "high": "11", "low": "9", "close": "10", "pre_close": "10", "change": "0", "pct_chg": "0", "vol": "100", "amount": "1000"}],
        [{"ts_code": "000001.SZ", "trade_date": "20260220", "adj_factor": "1.0"}],
        [{"ts_code": "000001.SZ", "trade_date": "20260220", "pe": "10"}],
    ]

    result = await gateway.fetch_stock_daily("000001.SZ", date(2026, 2, 1), date(2026, 2, 20))
    
    assert len(result) == 1
    assert result[0].third_code == "000001.SZ"
    assert mock_to_thread.call_count == 3


@pytest.mark.asyncio
async def test_token_bucket_rate_limiter():
    gateway = TuShareStockDailyGateway(token="dummy")
    
    # 修改限流器参数便于测试：容量 2，每秒补充 2
    gateway._rate_limiter._capacity = 2
    gateway._rate_limiter._tokens = 2
    gateway._rate_limiter._refill_rate = 2.0
    
    start_time = asyncio.get_event_loop().time()
    
    # 消费 3 个 token，前 2 个立即，第 3 个需要等 0.5s
    await gateway._rate_limiter.acquire()
    await gateway._rate_limiter.acquire()
    await gateway._rate_limiter.acquire()
    
    end_time = asyncio.get_event_loop().time()
    
    # 至少等待了 0.5 秒（补充 1 个 token 的时间）
    assert end_time - start_time >= 0.5
