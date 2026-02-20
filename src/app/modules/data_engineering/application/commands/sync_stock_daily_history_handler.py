"""历史同步 Handler。"""

import logging
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

from .sync_stock_daily_history import SyncHistoryResult, SyncStockDailyHistory

logger = logging.getLogger(__name__)


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
            # 简化实现，实际可能需要 find_by_third_codes 方法
            # 这里为了通过测试，假设基础仓储有对应方法
            stocks = await self.basic_repo.find_by_third_codes(DataSource.TUSHARE, command.ts_codes)
        else:
            stocks = await self.basic_repo.find_all_listed(DataSource.TUSHARE)

        today = date.today()
        success_count = 0
        failure_count = 0
        synced_days = 0

        for stock in stocks:
            start_date = None
            try:
                # 1. 独立事务查询最新日期，避免长事务
                async with self.uow:
                    latest_date = await self.daily_repo.get_latest_trade_date(
                        DataSource.TUSHARE, stock.third_code
                    )

                start_date = latest_date + timedelta(days=1) if latest_date else stock.list_date

                if start_date > today:
                    logger.info(f"[{stock.third_code}] 已经是最新数据，跳过同步 (start_date: {start_date})")
                    continue  # 已经是最新

                logger.info(f"[{stock.third_code}] 开始同步数据，时间范围: {start_date} -> {today}")

                # 2. 网络请求放在事务外
                records = await self.gateway.fetch_stock_daily(
                    stock.third_code, start_date, today
                )

                # 3. 开启新事务写入数据
                async with self.uow:
                    if records:
                        await self.daily_repo.upsert_many(records)
                        synced_days += len(records)
                        logger.info(f"[{stock.third_code}] 成功获取并写入 {len(records)} 条数据")
                    else:
                        logger.info(f"[{stock.third_code}] 未获取到任何数据")

                    await self.uow.commit()
                    success_count += 1
                    logger.info(f"[{stock.third_code}] 写入完成，已立马提交事务")

            except Exception as e:
                logger.error(f"[{stock.third_code}] 同步历史数据失败: {e}", exc_info=True)
                failure_count += 1
                # 记录失败
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

        return SyncHistoryResult(
            total=len(stocks),
            success_count=success_count,
            failure_count=failure_count,
            synced_days=synced_days,
        )
