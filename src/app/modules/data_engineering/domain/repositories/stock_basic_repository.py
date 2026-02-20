"""股票基础信息仓储接口。"""

from abc import ABC, abstractmethod

from ..entities.stock_basic import StockBasic
from ..value_objects.data_source import DataSource


class StockBasicRepository(ABC):
    """以 (source, third_code) 为唯一键批量 upsert；不 commit，由调用方 UnitOfWork 管理。"""

    @abstractmethod
    async def upsert_many(self, stocks: list[StockBasic]) -> None:
        """批量插入或更新。"""
        ...

    @abstractmethod
    async def find_by_third_codes(
        self, source: DataSource, third_codes: list[str]
    ) -> list[StockBasic]:
        """根据 source 和 third_codes 列表查询股票。"""
        ...

    @abstractmethod
    async def find_all_listed(self, source: DataSource) -> list[StockBasic]:
        """查询指定 source 下所有状态为 LISTED 的股票。"""
        ...

    @abstractmethod
    async def find_all(self, source: DataSource) -> list[StockBasic]:
        """查询指定 source 下所有股票（不限制状态）。"""
        ...
