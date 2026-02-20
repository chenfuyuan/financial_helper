"""SyncStockBasic 命令的 Handler：编排网关拉取 → 仓储 upsert，返回 synced_count。"""

from app.modules.data_engineering.domain.gateways import StockGateway
from app.modules.data_engineering.domain.repositories import StockBasicRepository
from app.shared_kernel.application.command_handler import CommandHandler
from app.shared_kernel.domain.unit_of_work import UnitOfWork

from .sync_stock_basic import SyncStockBasic


class SyncStockBasicHandler(CommandHandler[SyncStockBasic, int]):
    def __init__(self, gateway: StockGateway, repository: StockBasicRepository, uow: UnitOfWork) -> None:
        self._gateway = gateway
        self._repository = repository
        self._uow = uow

    async def handle(self, command: SyncStockBasic) -> int:
        stocks = await self._gateway.fetch_stock_basic()
        await self._repository.upsert_many(stocks)
        await self._uow.commit()
        return len(stocks)
