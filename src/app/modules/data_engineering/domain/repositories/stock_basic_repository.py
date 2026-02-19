"""股票基础信息仓储接口。"""

from abc import ABC, abstractmethod

from ..entities.stock_basic import StockBasic


class StockBasicRepository(ABC):
    """以 (source, third_code) 为唯一键批量 upsert；不 commit，由调用方 UnitOfWork 管理。"""

    @abstractmethod
    async def upsert_many(self, stocks: list[StockBasic]) -> None:
        """批量插入或更新。"""
        ...
