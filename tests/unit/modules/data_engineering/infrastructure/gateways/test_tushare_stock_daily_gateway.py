import asyncio
from datetime import date
from unittest.mock import patch

import pytest

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


def test_split_date_ranges_single_batch(gateway):
    """时间段在 365 天内，只产生一个批次。"""
    ranges = gateway._split_date_ranges(date(2024, 1, 1), date(2024, 6, 30))
    assert len(ranges) == 1
    assert ranges[0] == (date(2024, 1, 1), date(2024, 6, 30))


def test_split_date_ranges_multiple_batches(gateway):
    """时间段跨 2 年，2020-01-01 到 2021-12-31 共 731 天，按 365 天分批应产生 3 个批次。"""
    ranges = gateway._split_date_ranges(date(2020, 1, 1), date(2021, 12, 31), days_per_batch=365)
    assert len(ranges) == 3
    assert ranges[0][0] == date(2020, 1, 1)
    assert ranges[-1][1] == date(2021, 12, 31)


@pytest.mark.asyncio
@patch("app.modules.data_engineering.infrastructure.gateways.tushare_stock_daily_gateway.asyncio.to_thread")
async def test_fetch_stock_daily_multi_batch(mock_to_thread, gateway):
    """跨年数据拉取时应分多批调用 API，每批调用 3 个接口。"""

    def make_daily(trade_date: str) -> list[dict]:
        return [{"ts_code": "000001.SZ", "trade_date": trade_date, "open": "10",
                 "high": "11", "low": "9", "close": "10", "pre_close": "10",
                 "change": "0", "pct_chg": "0", "vol": "100", "amount": "1000"}]

    # 2020-01-01 到 2021-12-31 共 731 天，原设计分 3 批。
    # 因为现在实际拆分逻辑 batch size 是 5000，为了测试分批逻辑，我们直接 mock 拆分结果
    mock_to_thread.side_effect = [
        make_daily("20200601"), [], [],  # 第 1 批
        make_daily("20210101"), [], [],  # 第 2 批
        make_daily("20211001"), [], [],  # 第 3 批
    ]

    with patch.object(
        gateway, 
        "_split_date_ranges", 
        return_value=[
            (date(2020, 1, 1), date(2020, 6, 30)),
            (date(2020, 7, 1), date(2020, 12, 31)),
            (date(2021, 1, 1), date(2021, 12, 31)),
        ]
    ):
        result = await gateway.fetch_stock_daily("000001.SZ", date(2020, 1, 1), date(2021, 12, 31))

    # 3 批共 9 次 API 调用
    assert mock_to_thread.call_count == 9
    # 每批各有 1 条不同日期的 daily 数据，共 3 条
    assert len(result) == 3


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
