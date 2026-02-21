"""Tushare fina_indicator API 响应 → 领域实体 Mapper。"""

from dataclasses import fields as dc_fields
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from app.modules.data_engineering.domain.entities.stock_financial import StockFinancial
from app.modules.data_engineering.domain.value_objects.data_source import DataSource

_DATE_FIELDS = {"ann_date", "end_date"}
_STR_FIELDS = {"update_flag"}


def _d(val: str | int | float | None) -> Decimal | None:
    if val is None or val == "":
        return None
    try:
        return Decimal(str(val))
    except InvalidOperation:
        return None


def _dt(val: str | None) -> date | None:
    return datetime.strptime(val, "%Y%m%d").date() if val else None


class TuShareFinanceIndicatorMapper:
    """将 Tushare fina_indicator 接口返回的行字典转换为 StockFinancial 实体。"""

    @staticmethod
    def to_entity(row: dict) -> StockFinancial:
        kwargs: dict = {"id": None, "source": DataSource.TUSHARE, "third_code": row["ts_code"], "symbol": None}
        for f in dc_fields(StockFinancial):
            if f.name in {"id", "source", "third_code"}:
                continue
            v = row.get(f.name)
            if f.name in _DATE_FIELDS:
                kwargs[f.name] = _dt(v)
            elif f.name in _STR_FIELDS:
                kwargs[f.name] = v
            else:
                kwargs[f.name] = _d(v)
        return StockFinancial(**kwargs)
