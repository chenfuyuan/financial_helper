from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.modules.data_engineering.infrastructure.gateways.tushare_finance_indicator_gateway import (
    TuShareFinanceIndicatorGateway,
)


def _row(**kw):
    """构造最小 API 行，ts_code/end_date 必填，财务字段默认 None。"""
    defaults = {
        "ts_code": "000001.SZ",
        "ann_date": "20240330",
        "end_date": "20231231",
        "eps": "1.23",
        "update_flag": None,
    }
    defaults.update(kw)
    return defaults


@pytest.mark.asyncio
async def test_fetch_single_page():
    mock_pro = MagicMock()
    mock_pro.fina_indicator.return_value = MagicMock(
        to_dict=MagicMock(return_value=[_row()])
    )
    gw = TuShareFinanceIndicatorGateway(pro=mock_pro)
    results = await gw.fetch_by_stock("000001.SZ")
    assert len(results) == 1 and results[0].eps == Decimal("1.23")


@pytest.mark.asyncio
async def test_fetch_with_start_date():
    mock_pro = MagicMock()
    mock_pro.fina_indicator.return_value = MagicMock(
        to_dict=MagicMock(return_value=[])
    )
    gw = TuShareFinanceIndicatorGateway(pro=mock_pro)
    await gw.fetch_by_stock("000001.SZ", start_date=date(2023, 1, 1))
    assert mock_pro.fina_indicator.call_args.kwargs.get("start_date") == "20230101"


@pytest.mark.asyncio
async def test_pagination_stops_when_less_than_100():
    mock_pro = MagicMock()
    mock_pro.fina_indicator.return_value = MagicMock(
        to_dict=MagicMock(return_value=[_row()] * 50)
    )
    gw = TuShareFinanceIndicatorGateway(pro=mock_pro)
    results = await gw.fetch_by_stock("000001.SZ")
    assert mock_pro.fina_indicator.call_count == 1 and len(results) == 50
