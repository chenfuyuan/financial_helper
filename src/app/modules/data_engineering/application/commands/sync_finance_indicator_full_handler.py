"""财务指标全量同步 Handler。"""

from app.modules.data_engineering.domain.gateways.financial_indicator_gateway import (
    FinancialIndicatorGateway,
)
from app.modules.data_engineering.domain.repositories.financial_indicator_repository import (
    FinancialIndicatorRepository,
)
from app.modules.data_engineering.domain.repositories.stock_basic_repository import (
    StockBasicRepository,
)
from app.modules.data_engineering.domain.value_objects.data_source import DataSource
from app.shared_kernel.application.command_handler import CommandHandler
from app.shared_kernel.domain.unit_of_work import UnitOfWork
from app.shared_kernel.infrastructure.logging import get_logger

from .sync_finance_indicator_commands import (
    SyncFinanceIndicatorFull,
    SyncFinanceIndicatorResult,
)

logger = get_logger(__name__)


class SyncFinanceIndicatorFullHandler(
    CommandHandler[SyncFinanceIndicatorFull, SyncFinanceIndicatorResult]
):
    """全量同步：逐股拉取全部历史财务指标，每股独立事务，失败独立捕获继续。"""

    def __init__(
        self,
        basic_repo: StockBasicRepository,
        fi_repo: FinancialIndicatorRepository,
        gateway: FinancialIndicatorGateway,
        uow: UnitOfWork,
    ) -> None:
        self._basic_repo = basic_repo
        self._fi_repo = fi_repo
        self._gateway = gateway
        self._uow = uow

    async def handle(self, command: SyncFinanceIndicatorFull) -> SyncFinanceIndicatorResult:
        if command.ts_codes:
            stocks = await self._basic_repo.find_by_third_codes(
                DataSource.TUSHARE, command.ts_codes
            )
        else:
            stocks = await self._basic_repo.find_all(DataSource.TUSHARE)

        logger.info(
            "财务指标全量同步开始",
            command="SyncFinanceIndicatorFull",
            stock_count=len(stocks),
        )

        success_count = 0
        failure_count = 0
        synced_records = 0

        for stock in stocks:
            try:
                records = await self._gateway.fetch_by_stock(stock.third_code)
                async with self._uow:
                    if records:
                        await self._fi_repo.upsert_many(records)
                        synced_records += len(records)
                    await self._uow.commit()
                success_count += 1
                logger.info(
                    "单股财务指标全量同步完成",
                    third_code=stock.third_code,
                    record_count=len(records),
                )
            except Exception:
                failure_count += 1
                logger.error(
                    "单股财务指标全量同步失败",
                    third_code=stock.third_code,
                    exc_info=True,
                )

        result = SyncFinanceIndicatorResult(
            total=len(stocks),
            success_count=success_count,
            failure_count=failure_count,
            synced_records=synced_records,
        )
        logger.info(
            "财务指标全量同步结束",
            command="SyncFinanceIndicatorFull",
            total=result.total,
            success_count=result.success_count,
            failure_count=result.failure_count,
            synced_records=result.synced_records,
        )
        return result
