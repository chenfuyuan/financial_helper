"""历史同步 Handler。"""

from datetime import UTC, date, datetime, timedelta

from app.modules.data_engineering.domain.entities.stock_daily_sync_failure import (
    StockDailySyncFailure,
)
from app.modules.data_engineering.domain.gateways.stock_daily_gateway import StockDailyGateway
from app.modules.data_engineering.domain.repositories.stock_basic_repository import (
    StockBasicRepository,
)
from app.modules.data_engineering.domain.repositories.stock_daily_repository import (
    StockDailyRepository,
)
from app.modules.data_engineering.domain.repositories.stock_daily_sync_failure_repository import (
    StockDailySyncFailureRepository,
)
from app.modules.data_engineering.domain.value_objects.data_source import DataSource
from app.shared_kernel.application.command_handler import CommandHandler
from app.shared_kernel.domain.unit_of_work import UnitOfWork
from app.shared_kernel.infrastructure.logging import get_logger

from .sync_stock_daily_history import SyncHistoryResult, SyncStockDailyHistory

logger = get_logger(__name__)


class SyncStockDailyHistoryHandler(CommandHandler[SyncStockDailyHistory, SyncHistoryResult]):
    """历史同步 Handler。带断点续传、失败记录、独立事务。"""

    def __init__(
        self,
        gateway: StockDailyGateway,
        daily_repo: StockDailyRepository,
        basic_repo: StockBasicRepository,
        failure_repo: StockDailySyncFailureRepository,
        uow: UnitOfWork,
    ) -> None:
        self.gateway = gateway
        self.daily_repo = daily_repo
        self.basic_repo = basic_repo
        self.failure_repo = failure_repo
        self.uow = uow

    async def handle(self, command: SyncStockDailyHistory) -> SyncHistoryResult:
        if command.ts_codes:
            stocks = await self.basic_repo.find_by_third_codes(DataSource.TUSHARE, command.ts_codes)
        else:
            stocks = await self.basic_repo.find_all(DataSource.TUSHARE)

        today = date.today()
        logger.info(
            "历史同步开始",
            command="SyncStockDailyHistory",
            stock_count=len(stocks),
            ts_codes=command.ts_codes,
            today=str(today),
        )

        success_count = 0
        failure_count = 0
        synced_days = 0

        for stock in stocks:
            start_date = None
            try:
                async with self.uow:
                    latest_date = await self.daily_repo.get_latest_trade_date(DataSource.TUSHARE, stock.third_code)

                start_date = latest_date + timedelta(days=1) if latest_date else stock.list_date

                if start_date > today:
                    logger.info(
                        "已是最新数据，跳过同步",
                        third_code=stock.third_code,
                        start_date=str(start_date),
                    )
                    continue

                logger.info(
                    "开始同步单只股票历史数据",
                    third_code=stock.third_code,
                    start_date=str(start_date),
                    end_date=str(today),
                )

                records = await self.gateway.fetch_stock_daily(stock.third_code, start_date, today)

                async with self.uow:
                    if records:
                        await self.daily_repo.upsert_many(records)
                        synced_days += len(records)
                        logger.info(
                            "获取并写入日线数据完成",
                            third_code=stock.third_code,
                            record_count=len(records),
                        )
                    else:
                        logger.info(
                            "未获取到数据",
                            third_code=stock.third_code,
                            start_date=str(start_date),
                            end_date=str(today),
                        )

                    await self.uow.commit()
                    success_count += 1
                    logger.info(
                        "事务已提交",
                        third_code=stock.third_code,
                        success=True,
                    )

            except Exception as e:
                logger.error(
                    "同步历史数据失败",
                    third_code=stock.third_code,
                    start_date=str(start_date) if start_date else str(stock.list_date),
                    end_date=str(today),
                    error_message=str(e),
                    exc_info=True,
                )
                failure_count += 1
                async with self.uow:
                    failure = StockDailySyncFailure(
                        id=None,
                        source=DataSource.TUSHARE,
                        third_code=stock.third_code,
                        start_date=start_date or stock.list_date,
                        end_date=today,
                        error_message=str(e),
                        failed_at=datetime.now(UTC),
                        retry_count=0,
                        resolved=False,
                    )
                    await self.failure_repo.save(failure)
                    await self.uow.commit()

        result = SyncHistoryResult(
            total=len(stocks),
            success_count=success_count,
            failure_count=failure_count,
            synced_days=synced_days,
        )
        logger.info(
            "历史同步结束",
            command="SyncStockDailyHistory",
            total=result.total,
            success_count=result.success_count,
            failure_count=result.failure_count,
            synced_days=result.synced_days,
        )
        return result
