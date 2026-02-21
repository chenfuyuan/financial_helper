from dataclasses import fields
from datetime import date
from decimal import Decimal

from app.modules.data_engineering.domain.entities.stock_financial import StockFinancial
from app.modules.data_engineering.domain.value_objects.data_source import DataSource

_FIXED = {"id", "source", "third_code", "symbol", "end_date"}


def _make(**kwargs) -> StockFinancial:
    base = {
        "id": None,
        "source": DataSource.TUSHARE,
        "third_code": "000001.SZ",
        "symbol": None,
        "end_date": date(2023, 12, 31),
        **{f.name: None for f in fields(StockFinancial) if f.name not in _FIXED},
    }
    base.update(kwargs)
    return StockFinancial(**base)


def test_identity_by_id():
    assert _make(id=1) == _make(id=1)


def test_none_id_not_equal():
    assert _make(id=None) != _make(id=None)


def test_all_numeric_fields_accept_none():
    ind = _make(eps=None, roe=None, ann_date=None)
    assert ind.eps is None and ind.roe is None and ind.ann_date is None


def test_unique_key_fields():
    ind = _make(source=DataSource.TUSHARE, third_code="600000.SH", end_date=date(2023, 9, 30))
    assert (ind.source, ind.third_code, ind.end_date) == (
        DataSource.TUSHARE,
        "600000.SH",
        date(2023, 9, 30),
    )


def test_eps_decimal_precision():
    assert _make(eps=Decimal("1.2345")).eps == Decimal("1.2345")
