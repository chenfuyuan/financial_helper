"""data_engineering 模块专属依赖：组装 Gateway、Repository、Handler，供本模块 Router 注入。"""

from typing import TYPE_CHECKING

from fastapi import Depends

from app.config import settings
from app.interfaces.dependencies import get_uow
from app.modules.data_engineering.application.commands import (
    RetryStockDailySyncFailuresHandler,
    SyncConceptsHandler,
    SyncStockBasicHandler,
    SyncStockDailyHistoryHandler,
    SyncStockDailyIncrementHandler,
)
from app.modules.data_engineering.application.queries import (
    GetConceptsHandler,
    GetConceptStocksHandler,
)
from app.modules.data_engineering.infrastructure import (
    AkShareConceptGateway,
    SqlAlchemyConceptRepository,
    SqlAlchemyConceptStockRepository,
    SqlAlchemyStockBasicRepository,
    SqlAlchemyStockDailyRepository,
    SqlAlchemyStockDailySyncFailureRepository,
    TuShareStockDailyGateway,
    TuShareStockGateway,
)
from app.shared_kernel.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork

if TYPE_CHECKING:
    from app.modules.data_engineering.application.commands import (
        SyncFinanceIndicatorByStockHandler,
        SyncFinanceIndicatorFullHandler,
        SyncFinanceIndicatorIncrementHandler,
    )


def get_sync_stock_basic_handler(
    uow: SqlAlchemyUnitOfWork = Depends(get_uow),
) -> SyncStockBasicHandler:
    """构造 SyncStockBasic 的 Handler，供 /sync 等路由注入。"""
    gateway = TuShareStockGateway(token=settings.TUSHARE_TOKEN)
    repository = SqlAlchemyStockBasicRepository(uow.session)
    return SyncStockBasicHandler(gateway=gateway, repository=repository, uow=uow)


def get_sync_concepts_handler(
    uow: SqlAlchemyUnitOfWork = Depends(get_uow),
) -> SyncConceptsHandler:
    return SyncConceptsHandler(
        gateway=AkShareConceptGateway(),
        concept_repo=SqlAlchemyConceptRepository(uow.session),
        concept_stock_repo=SqlAlchemyConceptStockRepository(uow.session),
        stock_basic_repo=SqlAlchemyStockBasicRepository(uow.session),
        uow=uow,
    )


def get_get_concepts_handler(
    uow: SqlAlchemyUnitOfWork = Depends(get_uow),
) -> GetConceptsHandler:
    return GetConceptsHandler(concept_repo=SqlAlchemyConceptRepository(uow.session))


def get_get_concept_stocks_handler(
    uow: SqlAlchemyUnitOfWork = Depends(get_uow),
) -> GetConceptStocksHandler:
    return GetConceptStocksHandler(
        concept_repo=SqlAlchemyConceptRepository(uow.session),
        concept_stock_repo=SqlAlchemyConceptStockRepository(uow.session),
    )


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


def get_sync_finance_indicator_full_handler(
    uow: SqlAlchemyUnitOfWork = Depends(get_uow),
) -> "SyncFinanceIndicatorFullHandler":
    import tushare as ts  # type: ignore[import-untyped]

    from app.modules.data_engineering.application.commands import SyncFinanceIndicatorFullHandler
    from app.modules.data_engineering.infrastructure import (
        SqlAlchemyFinancialIndicatorRepository,
        TuShareFinanceIndicatorGateway,
    )

    pro = ts.pro_api(settings.TUSHARE_TOKEN)
    return SyncFinanceIndicatorFullHandler(
        basic_repo=SqlAlchemyStockBasicRepository(uow.session),
        fi_repo=SqlAlchemyFinancialIndicatorRepository(uow.session),
        gateway=TuShareFinanceIndicatorGateway(pro=pro),
        uow=uow,
    )


def get_sync_finance_indicator_by_stock_handler(
    uow: SqlAlchemyUnitOfWork = Depends(get_uow),
) -> "SyncFinanceIndicatorByStockHandler":
    import tushare as ts  # type: ignore[import-untyped]

    from app.modules.data_engineering.application.commands import SyncFinanceIndicatorByStockHandler
    from app.modules.data_engineering.infrastructure import (
        SqlAlchemyFinancialIndicatorRepository,
        TuShareFinanceIndicatorGateway,
    )

    pro = ts.pro_api(settings.TUSHARE_TOKEN)
    return SyncFinanceIndicatorByStockHandler(
        fi_repo=SqlAlchemyFinancialIndicatorRepository(uow.session),
        gateway=TuShareFinanceIndicatorGateway(pro=pro),
        uow=uow,
    )


def get_sync_finance_indicator_increment_handler(
    uow: SqlAlchemyUnitOfWork = Depends(get_uow),
) -> "SyncFinanceIndicatorIncrementHandler":
    import tushare as ts  # type: ignore[import-untyped]

    from app.modules.data_engineering.application.commands import (
        SyncFinanceIndicatorIncrementHandler,
    )
    from app.modules.data_engineering.infrastructure import (
        SqlAlchemyFinancialIndicatorRepository,
        TuShareFinanceIndicatorGateway,
    )

    pro = ts.pro_api(settings.TUSHARE_TOKEN)
    return SyncFinanceIndicatorIncrementHandler(
        basic_repo=SqlAlchemyStockBasicRepository(uow.session),
        fi_repo=SqlAlchemyFinancialIndicatorRepository(uow.session),
        gateway=TuShareFinanceIndicatorGateway(pro=pro),
        uow=uow,
    )
