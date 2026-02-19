"""股票基础信息同步 HTTP 接口。"""

import time

from fastapi import APIRouter, Depends

from app.config import settings
from app.interfaces.dependencies import get_uow
from app.interfaces.response import ApiResponse
from app.modules.data_engineering import application, infrastructure  # noqa: F401
from app.modules.data_engineering.application.commands.sync_stock_basic import SyncStockBasic
from app.modules.data_engineering.application.commands.sync_stock_basic_handler import (
    SyncStockBasicHandler,
)
from app.modules.data_engineering.infrastructure.gateways import TuShareStockGateway
from app.modules.data_engineering.infrastructure.repositories import (
    SqlAlchemyStockBasicRepository,
)
from app.shared_kernel.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork

router = APIRouter(prefix="/data-engineering/stock-basic", tags=["data_engineering"])


@router.post("/sync", response_model=ApiResponse[dict])
async def sync_stock_basic(
    uow: SqlAlchemyUnitOfWork = Depends(get_uow),
) -> ApiResponse[dict]:
    gateway = TuShareStockGateway(token=settings.TUSHARE_TOKEN)
    repository = SqlAlchemyStockBasicRepository(uow.session)
    handler = SyncStockBasicHandler(gateway=gateway, repository=repository)
    start = time.perf_counter()
    synced_count = await handler.handle(SyncStockBasic())
    await uow.commit()
    duration_ms = int((time.perf_counter() - start) * 1000)
    return ApiResponse.success(
        data={"synced_count": synced_count, "duration_ms": duration_ms},
        message="Sync completed",
    )
