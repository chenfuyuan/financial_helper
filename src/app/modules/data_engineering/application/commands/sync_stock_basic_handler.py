"""SyncStockBasic 命令的 Handler：编排网关拉取 → 仓储 upsert，返回 synced_count。"""

from app.modules.data_engineering import domain  # noqa: F401
from app.modules.data_engineering.domain.stock_basic_repository import StockBasicRepository
from app.modules.data_engineering.domain.stock_gateway import StockGateway
from app.shared_kernel.application.command_handler import CommandHandler

from .sync_stock_basic import SyncStockBasic


class SyncStockBasicHandler(CommandHandler[SyncStockBasic, int]):
    def __init__(self, gateway: StockGateway, repository: StockBasicRepository) -> None:
        self._gateway = gateway
        self._repository = repository

    async def handle(self, command: SyncStockBasic) -> int:
        stocks = await self._gateway.fetch_stock_basic()
        await self._repository.upsert_many(stocks)
        return len(stocks)
