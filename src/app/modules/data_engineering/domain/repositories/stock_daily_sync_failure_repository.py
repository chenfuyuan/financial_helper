"""股票日线行情同步失败记录仓储接口。"""

from abc import ABC, abstractmethod

from ..entities.stock_daily_sync_failure import StockDailySyncFailure


class StockDailySyncFailureRepository(ABC):
    """失败记录仓储。不 commit，由调用方 UnitOfWork 管理。"""

    @abstractmethod
    async def save(self, failure: StockDailySyncFailure) -> None:
        """保存失败记录（新增或更新 retry_count）。"""

    @abstractmethod
    async def find_unresolved(self, max_retries: int = 3) -> list[StockDailySyncFailure]:
        """查询未解决且 retry_count < max_retries 的失败记录。"""

    @abstractmethod
    async def mark_resolved(self, failure_id: int) -> None:
        """标记为已解决。"""
