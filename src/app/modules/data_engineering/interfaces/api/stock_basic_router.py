"""股票基础信息同步 HTTP 接口。"""

import time

from fastapi import APIRouter, Depends

from app.interfaces.response import ApiResponse
from app.modules.data_engineering.application.commands.sync_stock_basic import SyncStockBasic
from app.modules.data_engineering.application.commands.sync_stock_basic_handler import (
    SyncStockBasicHandler,
)
from app.modules.data_engineering.interfaces.dependencies import get_sync_stock_basic_handler

router = APIRouter(prefix="/data-engineering/stock-basic", tags=["data_engineering"])


@router.post("/sync", response_model=ApiResponse[dict])
async def sync_stock_basic(
    handler: SyncStockBasicHandler = Depends(get_sync_stock_basic_handler),
) -> ApiResponse[dict]:
    start = time.perf_counter()
    synced_count = await handler.handle(SyncStockBasic())
    duration_ms = int((time.perf_counter() - start) * 1000)
    return ApiResponse.success(
        data={"synced_count": synced_count, "duration_ms": duration_ms},
        message="Sync completed",
    )
