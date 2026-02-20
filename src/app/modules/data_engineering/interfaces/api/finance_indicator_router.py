"""财务指标同步 HTTP 接口。"""

from fastapi import APIRouter, Depends

from app.modules.data_engineering.application.commands.sync_finance_indicator_commands import (
    SyncFinanceIndicatorByStock,
    SyncFinanceIndicatorFull,
    SyncFinanceIndicatorIncrement,
)
from app.modules.data_engineering.interfaces.dependencies import (
    get_sync_finance_indicator_by_stock_handler,
    get_sync_finance_indicator_full_handler,
    get_sync_finance_indicator_increment_handler,
)

router = APIRouter(prefix="/data-engineering/finance-indicator", tags=["finance-indicator"])


@router.post("/sync/full")
async def sync_full(
    handler=Depends(get_sync_finance_indicator_full_handler),
):
    r = await handler.handle(SyncFinanceIndicatorFull())
    return r.__dict__


@router.post("/sync/by-stock/{ts_code}")
async def sync_by_stock(
    ts_code: str,
    handler=Depends(get_sync_finance_indicator_by_stock_handler),
):
    r = await handler.handle(SyncFinanceIndicatorByStock(ts_code=ts_code))
    return r.__dict__


@router.post("/sync/increment")
async def sync_increment(
    handler=Depends(get_sync_finance_indicator_increment_handler),
):
    r = await handler.handle(SyncFinanceIndicatorIncrement())
    return r.__dict__
