"""data_engineering 模块专属依赖：组装 Gateway、Repository、Handler，供本模块 Router 注入。"""

from fastapi import Depends

from app.config import settings
from app.interfaces.dependencies import get_uow
from app.modules.data_engineering.application.commands.sync_stock_basic_handler import (
    SyncStockBasicHandler,
)
from app.modules.data_engineering.infrastructure.gateways import TuShareStockGateway
from app.modules.data_engineering.infrastructure.repositories import (
    SqlAlchemyStockBasicRepository,
)
from app.shared_kernel.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


def get_sync_stock_basic_handler(
    uow: SqlAlchemyUnitOfWork = Depends(get_uow),
) -> SyncStockBasicHandler:
    """构造 SyncStockBasic 的 Handler，供 /sync 等路由注入。"""
    gateway = TuShareStockGateway(token=settings.TUSHARE_TOKEN)
    repository = SqlAlchemyStockBasicRepository(uow.session)
    return SyncStockBasicHandler(gateway=gateway, repository=repository, uow=uow)
