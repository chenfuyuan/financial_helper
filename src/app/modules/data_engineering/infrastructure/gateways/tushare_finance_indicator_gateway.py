"""TuShare 财务指标 Gateway：分页拉取 fina_indicator 接口，带 TokenBucket 限流。"""

import asyncio
from datetime import date

from app.modules.data_engineering.domain.gateways.financial_indicator_gateway import (
    FinancialIndicatorGateway,
)
from app.modules.data_engineering.infrastructure.gateways.tushare_stock_daily_gateway import (
    TokenBucket,
)
from app.shared_kernel.infrastructure.logging import get_logger

from .mappers.tushare_finance_indicator_mapper import TuShareFinanceIndicatorMapper

logger = get_logger(__name__)

PAGE_SIZE = 100


class TuShareFinanceIndicatorGateway(FinancialIndicatorGateway):
    """调用 Tushare fina_indicator 接口，检测式分页（返回 ≥100 行则继续翻页）。"""

    def __init__(self, pro, rate_limit: int = 200) -> None:
        self._pro = pro
        self._bucket = TokenBucket(capacity=rate_limit, tokens_per_minute=rate_limit)
        self._mapper = TuShareFinanceIndicatorMapper()

    async def fetch_by_stock(self, ts_code: str, start_date: date | None = None) -> list:
        results, offset = [], 0
        while True:
            await self._bucket.acquire()
            kw: dict = dict(ts_code=ts_code, limit=PAGE_SIZE, offset=offset)
            if start_date:
                kw["start_date"] = start_date.strftime("%Y%m%d")

            rows = (await asyncio.to_thread(self._pro.fina_indicator, **kw)).to_dict("records")

            if not rows:
                break

            results.extend(self._mapper.to_entity(r) for r in rows)
            logger.debug(
                "fina_indicator 分页拉取",
                ts_code=ts_code,
                offset=offset,
                got=len(rows),
            )

            if len(rows) < PAGE_SIZE:
                break
            offset += PAGE_SIZE

        return results
