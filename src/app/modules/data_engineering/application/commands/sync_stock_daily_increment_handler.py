"""增量同步 Handler。"""

import logging
from datetime import date, timedelta

from app.modules.data_engineering.domain.gateways.stock_daily_gateway import StockDailyGateway
from app.modules.data_engineering.domain.repositories.stock_daily_repository import (
    StockDailyRepository,
)
from app.shared_kernel.application.command_handler import CommandHandler
from app.shared_kernel.domain.unit_of_work import UnitOfWork

from .sync_stock_daily_increment import SyncIncrementResult, SyncStockDailyIncrement

logger = logging.getLogger(__name__)


class SyncStockDailyIncrementHandler(
    CommandHandler[SyncStockDailyIncrement, SyncIncrementResult]
):
    """增量同步 Handler。整体事务，失败即回滚抛异常。"""

    def __init__(
        self,
        gateway: StockDailyGateway,
        daily_repo: StockDailyRepository,
        uow: UnitOfWork,
    ) -> None:
        self.gateway = gateway
        self.daily_repo = daily_repo
        self.uow = uow

    async def handle(self, command: SyncStockDailyIncrement) -> SyncIncrementResult:
        trade_date = command.trade_date or (date.today() - timedelta(days=1))

        async with self.uow:
            records = await self.gateway.fetch_daily_all_by_date(trade_date)
            if records:
                await self.daily_repo.upsert_many(records)
            await self.uow.commit()

        return SyncIncrementResult(trade_date=trade_date, synced_count=len(records))
