"""data_engineering 模块专属依赖：组装 Gateway、Repository、Handler，供本模块 Router 注入。"""

from fastapi import Depends

from app.config import settings
from app.interfaces.dependencies import get_uow
from app.modules.data_engineering.application.commands.retry_stock_daily_sync_failures_handler import (
    RetryStockDailySyncFailuresHandler,
)
from app.modules.data_engineering.application.commands.sync_stock_basic_handler import (
    SyncStockBasicHandler,
)
from app.modules.data_engineering.application.commands.sync_stock_daily_history_handler import (
    SyncStockDailyHistoryHandler,
)
from app.modules.data_engineering.application.commands.sync_stock_daily_increment_handler import (
    SyncStockDailyIncrementHandler,
)
from app.modules.data_engineering.infrastructure.gateways import TuShareStockGateway
from app.modules.data_engineering.infrastructure.gateways.tushare_stock_daily_gateway import (
    TuShareStockDailyGateway,
)
from app.modules.data_engineering.infrastructure.repositories import (
    SqlAlchemyStockBasicRepository,
)
from app.modules.data_engineering.infrastructure.repositories.sqlalchemy_stock_daily_repository import (
    SqlAlchemyStockDailyRepository,
)
from app.modules.data_engineering.infrastructure.repositories.sqlalchemy_stock_daily_sync_failure_repository import (
    SqlAlchemyStockDailySyncFailureRepository,
)
from app.shared_kernel.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


def get_sync_stock_basic_handler(
    uow: SqlAlchemyUnitOfWork = Depends(get_uow),
) -> SyncStockBasicHandler:
    """构造 SyncStockBasic 的 Handler，供 /sync 等路由注入。"""
    gateway = TuShareStockGateway(token=settings.TUSHARE_TOKEN)
    repository = SqlAlchemyStockBasicRepository(uow.session)
    return SyncStockBasicHandler(gateway=gateway, repository=repository, uow=uow)


def get_sync_stock_daily_history_handler(
    uow: SqlAlchemyUnitOfWork = Depends(get_uow),
) -> SyncStockDailyHistoryHandler:
    gateway = TuShareStockDailyGateway(token=settings.TUSHARE_TOKEN)
    daily_repo = SqlAlchemyStockDailyRepository(uow.session)
    basic_repo = SqlAlchemyStockBasicRepository(uow.session)
    failure_repo = SqlAlchemyStockDailySyncFailureRepository(uow.session)
    return SyncStockDailyHistoryHandler(
        gateway=gateway,
        daily_repo=daily_repo,
        basic_repo=basic_repo,
        failure_repo=failure_repo,
        uow=uow,
    )


def get_sync_stock_daily_increment_handler(
    uow: SqlAlchemyUnitOfWork = Depends(get_uow),
) -> SyncStockDailyIncrementHandler:
    gateway = TuShareStockDailyGateway(token=settings.TUSHARE_TOKEN)
    daily_repo = SqlAlchemyStockDailyRepository(uow.session)
    return SyncStockDailyIncrementHandler(
        gateway=gateway,
        daily_repo=daily_repo,
        uow=uow,
    )


def get_retry_stock_daily_sync_failures_handler(
    uow: SqlAlchemyUnitOfWork = Depends(get_uow),
) -> RetryStockDailySyncFailuresHandler:
    gateway = TuShareStockDailyGateway(token=settings.TUSHARE_TOKEN)
    daily_repo = SqlAlchemyStockDailyRepository(uow.session)
    failure_repo = SqlAlchemyStockDailySyncFailureRepository(uow.session)
    return RetryStockDailySyncFailuresHandler(
        gateway=gateway,
        daily_repo=daily_repo,
        failure_repo=failure_repo,
        uow=uow,
    )
