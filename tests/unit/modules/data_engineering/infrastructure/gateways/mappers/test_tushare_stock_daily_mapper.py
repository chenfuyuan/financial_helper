from datetime import date
from decimal import Decimal

import pytest

from app.modules.data_engineering.domain.exceptions import ExternalStockServiceError
from app.modules.data_engineering.infrastructure import TuShareStockDailyMapper


def test_merge_daily_data():
    mapper = TuShareStockDailyMapper()

    daily_row = {
        "ts_code": "000001.SZ",
        "trade_date": "20260220",
        "open": "10.0",
        "high": "11.0",
        "low": "9.0",
        "close": "10.5",
        "pre_close": "9.5",
        "change": "1.0",
        "pct_chg": "10.0",
        "vol": "100.0",
        "amount": "1000.0",
    }

    adj_row = {
        "ts_code": "000001.SZ",
        "trade_date": "20260220",
        "adj_factor": "1.5",
    }

    basic_row = {
        "ts_code": "000001.SZ",
        "trade_date": "20260220",
        "turnover_rate": "1.2",
        "turnover_rate_f": "1.3",
        "volume_ratio": "1.4",
        "pe": "10.1",
        "pe_ttm": "10.2",
        "pb": "1.1",
        "ps": "2.1",
        "ps_ttm": "2.2",
        "dv_ratio": "3.1",
        "dv_ttm": "3.2",
        "total_share": "10000.0",
        "float_share": "5000.0",
        "free_share": "4000.0",
        "total_mv": "100000.0",
        "circ_mv": "50000.0",
    }

    result = mapper.merge_to_stock_daily("000001.SZ", [daily_row], [adj_row], [basic_row])

    assert len(result) == 1
    stock = result[0]
    assert stock.third_code == "000001.SZ"
    assert stock.trade_date == date(2026, 2, 20)
    assert stock.open == Decimal("10.0")
    assert stock.adj_factor == Decimal("1.5")
    assert stock.pe == Decimal("10.1")


def test_merge_missing_daily_basic_fields():
    mapper = TuShareStockDailyMapper()

    daily_row = {
        "ts_code": "000001.SZ",
        "trade_date": "20260220",
        "open": "10.0",
        "high": "11.0",
        "low": "9.0",
        "close": "10.5",
        "pre_close": "9.5",
        "change": "1.0",
        "pct_chg": "10.0",
        "vol": "100.0",
        "amount": "1000.0",
    }

    adj_row = {
        "ts_code": "000001.SZ",
        "trade_date": "20260220",
        "adj_factor": "1.5",
    }

    # 模拟停牌股，daily_basic 缺乏数据或为 None
    basic_row = {
        "ts_code": "000001.SZ",
        "trade_date": "20260220",
        "turnover_rate": None,
        "pe": None,
        # missing volume_ratio
    }

    result = mapper.merge_to_stock_daily("000001.SZ", [daily_row], [adj_row], [basic_row])
    assert len(result) == 1
    stock = result[0]
    assert stock.turnover_rate is None
    assert stock.volume_ratio is None
    assert stock.pe is None


def test_missing_required_daily_fields_raises_error():
    mapper = TuShareStockDailyMapper()

    daily_row = {
        "ts_code": "000001.SZ",
        "trade_date": "20260220",
        # missing open
    }
    adj_row = {"ts_code": "000001.SZ", "trade_date": "20260220", "adj_factor": "1.5"}

    with pytest.raises(ExternalStockServiceError, match="Missing required field: open"):
        mapper.merge_to_stock_daily("000001.SZ", [daily_row], [adj_row], [])
