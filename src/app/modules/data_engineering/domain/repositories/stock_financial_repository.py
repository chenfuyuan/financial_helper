"""股票财务指标仓储接口。"""

from abc import ABC, abstractmethod
from datetime import date

from ..entities.stock_financial import StockFinancial
from ..value_objects.data_source import DataSource


class StockFinancialRepository(ABC):
    """以 (source, third_code, end_date) 为唯一键批量 upsert；
    不 commit，由调用方 UnitOfWork 管理。
    """

    @abstractmethod
    async def upsert_many(self, records: list[StockFinancial]) -> None:
        """批量 upsert，不 commit，由 UnitOfWork 管理。"""

    @abstractmethod
    async def get_latest_end_date(self, source: DataSource, third_code: str) -> date | None:
        """查最新报告期截止日，无记录返回 None。"""
