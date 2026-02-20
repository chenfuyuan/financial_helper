"""增量同步 Handler。"""

from datetime import date, timedelta

from app.modules.data_engineering.domain.gateways.stock_daily_gateway import StockDailyGateway
from app.modules.data_engineering.domain.repositories.stock_daily_repository import (
    StockDailyRepository,
)
from app.shared_kernel.application.command_handler import CommandHandler
from app.shared_kernel.domain.unit_of_work import UnitOfWork
from app.shared_kernel.infrastructure.logging import get_logger

from .sync_stock_daily_increment import SyncIncrementResult, SyncStockDailyIncrement

logger = get_logger(__name__)


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
        logger.info(
            "增量同步开始",
            command="SyncStockDailyIncrement",
            trade_date=str(trade_date),
        )

        async with self.uow:
            records = await self.gateway.fetch_daily_all_by_date(trade_date)
            logger.info(
                "拉取日线全市场数据完成",
                trade_date=str(trade_date),
                record_count=len(records),
            )
            if records:
                await self.daily_repo.upsert_many(records)
                logger.info("批量写入完成", trade_date=str(trade_date), upsert_count=len(records))
            await self.uow.commit()

        result = SyncIncrementResult(trade_date=trade_date, synced_count=len(records))
        logger.info(
            "增量同步结束",
            command="SyncStockDailyIncrement",
            trade_date=str(trade_date),
            synced_count=result.synced_count,
        )
        return result
