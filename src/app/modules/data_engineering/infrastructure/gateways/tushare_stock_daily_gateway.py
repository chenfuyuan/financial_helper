"""TuShare 股票日线数据网关：拉取数据并委托 Mapper 解析。带 Token Bucket 限流。"""

import asyncio
from datetime import date
from typing import Any

from app.modules.data_engineering.domain.entities.stock_daily import StockDaily
from app.modules.data_engineering.domain.exceptions import ExternalStockServiceError
from app.modules.data_engineering.domain.gateways.stock_daily_gateway import StockDailyGateway

from .mappers.tushare_stock_daily_mapper import TuShareStockDailyMapper


class TokenBucket:
    """令牌桶限流器。"""

    def __init__(self, capacity: int, tokens_per_minute: int):
        self._capacity = capacity
        self._tokens = float(capacity)
        self._refill_rate = tokens_per_minute / 60.0  # tokens per second
        self._last_refill: float = 0.0
        self._lock: asyncio.Lock | None = None

    async def acquire(self) -> None:
        """获取一个令牌，若不足则等待。"""
        if self._lock is None:
            self._lock = asyncio.Lock()
            self._last_refill = asyncio.get_running_loop().time()

        async with self._lock:
            now = asyncio.get_running_loop().time()
            # 补充令牌
            elapsed = now - self._last_refill
            self._tokens = min(self._capacity, self._tokens + elapsed * self._refill_rate)
            self._last_refill = now

            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return

            # 计算需要等待的时间
            wait_time = (1.0 - self._tokens) / self._refill_rate
            await asyncio.sleep(wait_time)
            
            # 等待后直接扣除
            self._tokens = 0.0
            self._last_refill = asyncio.get_running_loop().time()


class TuShareStockDailyGateway(StockDailyGateway):
    """调用 TuShare 接口，拉取数据后使用 Mapper 合并解析。"""

    def __init__(self, token: str, mapper: TuShareStockDailyMapper | None = None) -> None:
        self._token = token
        self._mapper = mapper or TuShareStockDailyMapper()
        # 每分钟 200 次调用
        self._rate_limiter = TokenBucket(capacity=200, tokens_per_minute=200)

    async def _fetch_api(self, api_name: str, **kwargs) -> list[dict[str, Any]]:
        """调用单个 API 并返回数据列表。"""
        await self._rate_limiter.acquire()
        import tushare as ts  # type: ignore[import-untyped]

        def _sync_fetch() -> list[dict[str, Any]]:
            pro = ts.pro_api(self._token)
            method = getattr(pro, api_name)
            df = method(**kwargs)
            if df is None or df.empty:
                return []
            return list(df.to_dict("records"))

        try:
            return await asyncio.to_thread(_sync_fetch)
        except Exception as e:
            raise ExternalStockServiceError(f"TuShare API {api_name} error: {e}") from e

    async def fetch_stock_daily(
        self, ts_code: str, start_date: date, end_date: date
    ) -> list[StockDaily]:
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")

        daily_data = await self._fetch_api(
            "daily", ts_code=ts_code, start_date=start_str, end_date=end_str
        )
        if not daily_data:
            return []

        adj_data = await self._fetch_api(
            "adj_factor", ts_code=ts_code, start_date=start_str, end_date=end_str
        )
        basic_data = await self._fetch_api(
            "daily_basic", ts_code=ts_code, start_date=start_str, end_date=end_str
        )

        return self._mapper.merge_to_stock_daily(ts_code, daily_data, adj_data, basic_data)

    async def fetch_daily_all_by_date(self, trade_date: date) -> list[StockDaily]:
        date_str = trade_date.strftime("%Y%m%d")
        # 实际全市场约 5000 只，通常不用分页。为了健壮，TuShare 若后续需要分页则在此处实现循环拉取
        # 当前基于 TuShare 文档，传入 trade_date 一次性返回当日所有股票数据
        
        daily_data = await self._fetch_api("daily", trade_date=date_str)
        if not daily_data:
            return []

        adj_data = await self._fetch_api("adj_factor", trade_date=date_str)
        basic_data = await self._fetch_api("daily_basic", trade_date=date_str)

        # 全量时 mapper 需能按不同 ts_code 拆分合并
        # 为了复用 mapper，这里我们先按 ts_code 分组，然后再合并
        result = []
        codes = {r.get("ts_code") for r in daily_data if r.get("ts_code")}
        
        # 将三份数据建立 {ts_code: [rows]} 的索引
        daily_by_code: dict[str, list[dict]] = {c: [] for c in codes}
        adj_by_code: dict[str, list[dict]] = {c: [] for c in codes}
        basic_by_code: dict[str, list[dict]] = {c: [] for c in codes}
        
        for r in daily_data:
            if c := str(r.get("ts_code")):
                daily_by_code[c].append(r)
        for r in adj_data:
            c = str(r.get("ts_code"))
            if c and c in adj_by_code:
                adj_by_code[c].append(r)
        for r in basic_data:
            c = str(r.get("ts_code"))
            if c and c in basic_by_code:
                basic_by_code[c].append(r)

        for code in codes:
            d = daily_by_code.get(code, [])
            a = adj_by_code.get(code, [])
            b = basic_by_code.get(code, [])
            if d:
                stocks = self._mapper.merge_to_stock_daily(code, d, a, b)
                result.extend(stocks)
                
        return result
