"""重试失败记录 Handler。"""

import logging
from datetime import datetime, UTC

from app.shared_kernel.application.command_handler import CommandHandler
from app.shared_kernel.domain.unit_of_work import UnitOfWork
from app.modules.data_engineering.domain.gateways.stock_daily_gateway import StockDailyGateway
from app.modules.data_engineering.domain.repositories.stock_daily_repository import (
    StockDailyRepository,
)
from app.modules.data_engineering.domain.repositories.stock_daily_sync_failure_repository import (
    StockDailySyncFailureRepository,
)

from .sync_stock_daily_increment import RetryResult, RetryStockDailySyncFailures

logger = logging.getLogger(__name__)


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
        # 注意：使用单独的 uow instance 包裹查询，避免和下面循环内的事务冲突
        # 更好的做法是在接口层注入一个新的 session，这里为了简化，我们在外部开启查询事务
        async with self.uow:
            failures = await self.failure_repo.find_unresolved(max_retries=command.max_retries)

        if not failures:
            return RetryResult(total=0, resolved_count=0, still_failed_count=0)

        resolved_count = 0
        still_failed_count = 0

        for failure in failures:
            if not failure.id:
                continue

            try:
                # 重新尝试同步数据
                records = await self.gateway.fetch_stock_daily(
                    failure.third_code, failure.start_date, failure.end_date
                )

                async with self.uow:
                    if records:
                        await self.daily_repo.upsert_many(records)
                    await self.failure_repo.mark_resolved(failure.id)
                    await self.uow.commit()

                resolved_count += 1
                logger.info(f"Successfully retried {failure.third_code}")

            except Exception as e:
                logger.warning(f"Retry failed for {failure.third_code}: {e}")
                still_failed_count += 1
                
                async with self.uow:
                    failure.retry_count += 1
                    failure.error_message = str(e)
                    failure.failed_at = datetime.now(UTC)
                    await self.failure_repo.save(failure)
                    await self.uow.commit()

        return RetryResult(
            total=len(failures),
            resolved_count=resolved_count,
            still_failed_count=still_failed_count,
        )
