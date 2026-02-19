"""TuShare 股票基础信息网关：拉取原始数据并委托 Mapper 解析为 StockBasic。"""

import asyncio
from typing import Any

from app.modules.data_engineering.domain.entities.stock_basic import StockBasic
from app.modules.data_engineering.domain.gateways import StockGateway

from .mappers.tushare_stock_basic_mapper import TuShareStockBasicMapper


class TuShareStockGateway(StockGateway):
    """调用 TuShare stock_basic，拉取后经 Mapper 解析；解析失败即抛 ExternalStockServiceError。"""

    def __init__(self, token: str, mapper: TuShareStockBasicMapper | None = None) -> None:
        self._token = token
        self._mapper = mapper or TuShareStockBasicMapper()

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
            result.append(self._mapper.row_to_stock(row))
        return result
