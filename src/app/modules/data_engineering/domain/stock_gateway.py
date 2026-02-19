"""股票数据网关接口。"""

from abc import ABC, abstractmethod

from .stock_basic import StockBasic


class StockGateway(ABC):
    """从外部数据源拉取股票基础信息。任一条解析失败即抛异常，不返回部分结果。"""

    @abstractmethod
    async def fetch_stock_basic(self) -> list[StockBasic]:
        """拉取股票基础信息列表。"""
        ...
