"""股票日线数据网关接口。"""

from abc import ABC, abstractmethod
from datetime import date

from ..entities.stock_daily import StockDaily


class StockDailyGateway(ABC):
    """从外部数据源拉取股票日线行情。内部封装 daily、adj_factor、daily_basic 的调用与组装。"""

    @abstractmethod
    async def fetch_stock_daily(
        self, ts_code: str, start_date: date, end_date: date
    ) -> list[StockDaily]:
        """获取单只股票指定日期范围的完整日线数据。"""

    @abstractmethod
    async def fetch_daily_all_by_date(self, trade_date: date) -> list[StockDaily]:
        """获取某一交易日所有股票的完整日线数据。内部处理 TuShare 分页（单次 ≤5000 条）。"""
