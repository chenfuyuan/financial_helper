"""TuShare 股票基础信息网关：拉取并解析为 StockBasic，任一条解析失败即抛异常。"""

import asyncio
from datetime import UTC, date, datetime
from typing import Any

from app.modules.data_engineering.domain.exceptions import ExternalStockServiceError
from app.modules.data_engineering.domain.stock_basic import DataSource, StockBasic, StockStatus
from app.modules.data_engineering.domain.stock_gateway import StockGateway


def _parse_list_date(value: Any) -> date:
    """将 YYYYMMDD 字符串或可解析值转为 date，解析失败抛 ExternalStockServiceError。"""
    if value is None:
        raise ExternalStockServiceError("list_date is required")
    s = str(value).strip()
    if len(s) != 8 or not s.isdigit():
        raise ExternalStockServiceError(f"Invalid list_date format: {value!r}")
    try:
        return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    except ValueError as e:
        raise ExternalStockServiceError(f"Invalid list_date: {value!r}") from e


def _parse_list_status(value: Any) -> StockStatus:
    """L→LISTED, D→DELISTED, P→SUSPENDED。"""
    if value is None:
        raise ExternalStockServiceError("list_status is required")
    s = str(value).strip().upper()
    if s == "L":
        return StockStatus.LISTED
    if s == "D":
        return StockStatus.DELISTED
    if s == "P":
        return StockStatus.SUSPENDED
    raise ExternalStockServiceError(f"Unknown list_status: {value!r}")


def _row_to_stock(row: dict[str, Any]) -> StockBasic:
    """单行 dict 转为 StockBasic，缺字段或格式错误抛 ExternalStockServiceError。"""
    ts_code = row.get("ts_code")
    if not ts_code:
        raise ExternalStockServiceError("ts_code is required")
    symbol = row.get("symbol") or ""
    name = row.get("name") or ""
    market = row.get("market") or ""
    area = row.get("area") or ""
    industry = row.get("industry") or ""
    list_date = _parse_list_date(row.get("list_date"))
    status = _parse_list_status(row.get("list_status"))
    now = datetime.now(UTC)
    return StockBasic(
        id=None,
        created_at=now,
        updated_at=now,
        version=0,
        source=DataSource.TUSHARE,
        third_code=str(ts_code).strip(),
        symbol=str(symbol).strip(),
        name=str(name).strip(),
        market=str(market).strip(),
        area=str(area).strip(),
        industry=str(industry).strip(),
        list_date=list_date,
        status=status,
    )


class TuShareStockGateway(StockGateway):
    """调用 TuShare stock_basic，逐条解析为 StockBasic；解析失败即抛 ExternalStockServiceError。"""

    def __init__(self, token: str) -> None:
        self._token = token

    async def _fetch_raw(self) -> list[dict[str, Any]]:
        """拉取原始数据（list of dict）。可被单测 patch。"""
        import tushare as ts  # type: ignore[import-untyped]

        def _sync_fetch() -> list[dict[str, Any]]:
            pro = ts.pro_api(self._token)
            df = pro.stock_basic(
                exchange="",
                list_status="",
                fields="ts_code,symbol,name,market,area,industry,list_date,list_status",
            )
            if df is None or df.empty:
                return []
            return list(df.to_dict("records"))

        return await asyncio.to_thread(_sync_fetch)

    async def fetch_stock_basic(self) -> list[StockBasic]:
        raw = await self._fetch_raw()
        result: list[StockBasic] = []
        for row in raw:
            result.append(_row_to_stock(row))
        return result
