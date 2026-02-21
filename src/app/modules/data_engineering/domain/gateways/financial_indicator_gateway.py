"""财务指标网关接口。"""

from abc import ABC, abstractmethod
from datetime import date

from ..entities.stock_financial import StockFinancial


class FinancialIndicatorGateway(ABC):
    """从外部数据源拉取财务指标数据。内部封装分页逻辑。"""

    @abstractmethod
    async def fetch_by_stock(self, ts_code: str, start_date: date | None = None) -> list[StockFinancial]:
        """拉取单只股票所有历史财务指标（含检测式分页）。"""
