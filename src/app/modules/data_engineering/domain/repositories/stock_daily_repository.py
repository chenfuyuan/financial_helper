"""股票日线行情仓储接口。"""

from abc import ABC, abstractmethod
from datetime import date

from ..entities.stock_daily import StockDaily
from ..value_objects.data_source import DataSource


class StockDailyRepository(ABC):
    """以 (source, third_code, trade_date) 为唯一键批量 upsert；不 commit，由调用方 UnitOfWork 管理。"""

    @abstractmethod
    async def upsert_many(self, records: list[StockDaily]) -> None:
        """以 (source, third_code, trade_date) 为唯一键批量 upsert。不 commit。"""

    @abstractmethod
    async def get_latest_trade_date(self, source: DataSource, third_code: str) -> date | None:
        """查询某只股票本地已有的最新交易日期，用于断点续传。无记录返回 None。"""
