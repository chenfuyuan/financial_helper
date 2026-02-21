"""财务指标单股同步 Handler。"""

from app.modules.data_engineering.domain.gateways.financial_indicator_gateway import (
    FinancialIndicatorGateway,
)
from app.modules.data_engineering.domain.repositories.stock_financial_repository import (
    StockFinancialRepository,
)
from app.modules.data_engineering.domain.repositories.stock_basic_repository import (
    StockBasicRepository,
)
from app.modules.data_engineering.domain.value_objects.data_source import DataSource
from app.shared_kernel.application.command_handler import CommandHandler
from app.shared_kernel.domain.unit_of_work import UnitOfWork
from app.shared_kernel.infrastructure.logging import get_logger

from .sync_finance_indicator_commands import (
    SyncFinanceIndicatorByStock,
    SyncFinanceIndicatorResult,
)

logger = get_logger(__name__)


class SyncFinanceIndicatorByStockHandler(CommandHandler[SyncFinanceIndicatorByStock, SyncFinanceIndicatorResult]):
    """单股同步：拉取单只股票全部历史财务指标，单次事务。"""

    def __init__(
        self,
        basic_repo: StockBasicRepository,
        fi_repo: StockFinancialRepository,
        gateway: FinancialIndicatorGateway,
        uow: UnitOfWork,
    ) -> None:
        self._basic_repo = basic_repo
        self._fi_repo = fi_repo
        self._gateway = gateway
        self._uow = uow

    async def handle(self, command: SyncFinanceIndicatorByStock) -> SyncFinanceIndicatorResult:
        logger.info(
            "财务指标单股同步开始",
            command="SyncFinanceIndicatorByStock",
            ts_code=command.ts_code,
        )
        
        # 获取stock_basic信息以得到symbol
        stocks = await self._basic_repo.find_by_third_codes(DataSource.TUSHARE, [command.ts_code])
        if not stocks:
            logger.error(
                "未找到股票基础信息",
                ts_code=command.ts_code,
            )
            raise ValueError(f"未找到股票基础信息: {command.ts_code}")
        
        stock = stocks[0]
        
        records = await self._gateway.fetch_by_stock(command.ts_code)
        # 填充symbol字段
        for record in records:
            record.symbol = stock.symbol
        
        async with self._uow:
            if records:
                await self._fi_repo.upsert_many(records)
            await self._uow.commit()

        result = SyncFinanceIndicatorResult(
            total=1,
            success_count=1,
            failure_count=0,
            synced_records=len(records),
        )
        logger.info(
            "财务指标单股同步结束",
            command="SyncFinanceIndicatorByStock",
            ts_code=command.ts_code,
            synced_records=result.synced_records,
        )
        return result
