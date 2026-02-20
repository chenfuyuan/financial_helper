"""重试失败记录 Handler。"""

from datetime import UTC, datetime

from app.modules.data_engineering.domain.gateways.stock_daily_gateway import StockDailyGateway
from app.modules.data_engineering.domain.repositories.stock_daily_repository import (
    StockDailyRepository,
)
from app.modules.data_engineering.domain.repositories.stock_daily_sync_failure_repository import (
    StockDailySyncFailureRepository,
)
from app.shared_kernel.application.command_handler import CommandHandler
from app.shared_kernel.domain.unit_of_work import UnitOfWork
from app.shared_kernel.infrastructure.logging import get_logger

from .sync_stock_daily_increment import RetryResult, RetryStockDailySyncFailures

logger = get_logger(__name__)


class RetryStockDailySyncFailuresHandler(CommandHandler[RetryStockDailySyncFailures, RetryResult]):
    """重试失败记录 Handler。查询未解决且未超限的记录，逐个重试。"""

    def __init__(
        self,
        gateway: StockDailyGateway,
        daily_repo: StockDailyRepository,
        failure_repo: StockDailySyncFailureRepository,
        uow: UnitOfWork,
    ) -> None:
        self.gateway = gateway
        self.daily_repo = daily_repo
        self.failure_repo = failure_repo
        self.uow = uow

    async def handle(self, command: RetryStockDailySyncFailures) -> RetryResult:
        async with self.uow:
            failures = await self.failure_repo.find_unresolved(max_retries=command.max_retries)

        logger.info(
            "重试失败记录开始",
            command="RetryStockDailySyncFailures",
            max_retries=command.max_retries,
            failure_count=len(failures),
        )

        if not failures:
            logger.info("无待重试记录，直接返回", command="RetryStockDailySyncFailures")
            return RetryResult(total=0, resolved_count=0, still_failed_count=0)

        resolved_count = 0
        still_failed_count = 0

        for failure in failures:
            if not failure.id:
                continue

            try:
                logger.info(
                    "开始重试单条失败记录",
                    failure_id=failure.id,
                    third_code=failure.third_code,
                    start_date=str(failure.start_date),
                    end_date=str(failure.end_date),
                )

                records = await self.gateway.fetch_stock_daily(failure.third_code, failure.start_date, failure.end_date)

                async with self.uow:
                    if records:
                        await self.daily_repo.upsert_many(records)
                        logger.info(
                            "重试写入日线数据完成",
                            third_code=failure.third_code,
                            record_count=len(records),
                        )
                    await self.failure_repo.mark_resolved(failure.id)
                    await self.uow.commit()

                resolved_count += 1
                logger.info(
                    "重试成功",
                    third_code=failure.third_code,
                    failure_id=failure.id,
                )

            except Exception as e:
                logger.warning(
                    "重试失败",
                    third_code=failure.third_code,
                    failure_id=failure.id,
                    start_date=str(failure.start_date),
                    end_date=str(failure.end_date),
                    error_message=str(e),
                    exc_info=True,
                )
                still_failed_count += 1

                async with self.uow:
                    failure.retry_count += 1
                    failure.error_message = str(e)
                    failure.failed_at = datetime.now(UTC)
                    await self.failure_repo.save(failure)
                    await self.uow.commit()

        result = RetryResult(
            total=len(failures),
            resolved_count=resolved_count,
            still_failed_count=still_failed_count,
        )
        logger.info(
            "重试失败记录结束",
            command="RetryStockDailySyncFailures",
            total=result.total,
            resolved_count=result.resolved_count,
            still_failed_count=result.still_failed_count,
        )
        return result
