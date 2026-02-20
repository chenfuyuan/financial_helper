"""股票日线数据同步 HTTP 接口。"""

import time
from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.interfaces.response import ApiResponse
from app.modules.data_engineering.application.commands.retry_stock_daily_sync_failures_handler import (
    RetryStockDailySyncFailuresHandler,
)
from app.modules.data_engineering.application.commands.sync_stock_daily_history import (
    SyncStockDailyHistory,
)
from app.modules.data_engineering.application.commands.sync_stock_daily_history_handler import (
    SyncStockDailyHistoryHandler,
)
from app.modules.data_engineering.application.commands.sync_stock_daily_increment import (
    RetryStockDailySyncFailures,
    SyncStockDailyIncrement,
)
from app.modules.data_engineering.application.commands.sync_stock_daily_increment_handler import (
    SyncStockDailyIncrementHandler,
)
from app.modules.data_engineering.interfaces.dependencies import (
    get_retry_stock_daily_sync_failures_handler,
    get_sync_stock_daily_history_handler,
    get_sync_stock_daily_increment_handler,
)

router = APIRouter(prefix="/data-engineering/stock-daily", tags=["data_engineering"])


class SyncHistoryRequest(BaseModel):
    ts_codes: list[str] | None = None


class SyncIncrementRequest(BaseModel):
    trade_date: date | None = None


class RetryFailuresRequest(BaseModel):
    max_retries: int = 3


@router.post("/sync/history", response_model=ApiResponse[dict])
async def sync_stock_daily_history(
    request: SyncHistoryRequest | None = None,
    handler: SyncStockDailyHistoryHandler = Depends(get_sync_stock_daily_history_handler),
) -> ApiResponse[dict]:
    start = time.perf_counter()
    ts_codes = request.ts_codes if request else None
    result = await handler.handle(SyncStockDailyHistory(ts_codes=ts_codes))
    duration_ms = int((time.perf_counter() - start) * 1000)

    return ApiResponse.success(
        data={
            "total": result.total,
            "success_count": result.success_count,
            "failure_count": result.failure_count,
            "synced_days": result.synced_days,
            "duration_ms": duration_ms,
        },
        message="History sync completed",
    )


@router.post("/sync/increment", response_model=ApiResponse[dict])
async def sync_stock_daily_increment(
    request: SyncIncrementRequest | None = None,
    handler: SyncStockDailyIncrementHandler = Depends(get_sync_stock_daily_increment_handler),
) -> ApiResponse[dict]:
    start = time.perf_counter()
    trade_date = request.trade_date if request else None
    result = await handler.handle(SyncStockDailyIncrement(trade_date=trade_date))
    duration_ms = int((time.perf_counter() - start) * 1000)

    return ApiResponse.success(
        data={
            "trade_date": result.trade_date.isoformat(),
            "synced_count": result.synced_count,
            "duration_ms": duration_ms,
        },
        message="Increment sync completed",
    )


@router.post("/sync/retry-failures", response_model=ApiResponse[dict])
async def retry_stock_daily_sync_failures(
    request: RetryFailuresRequest | None = None,
    handler: RetryStockDailySyncFailuresHandler = Depends(
        get_retry_stock_daily_sync_failures_handler
    ),
) -> ApiResponse[dict]:
    start = time.perf_counter()
    max_retries = request.max_retries if request else 3
    result = await handler.handle(RetryStockDailySyncFailures(max_retries=max_retries))
    duration_ms = int((time.perf_counter() - start) * 1000)

    return ApiResponse.success(
        data={
            "total": result.total,
            "resolved_count": result.resolved_count,
            "still_failed_count": result.still_failed_count,
            "duration_ms": duration_ms,
        },
        message="Retry failures completed",
    )
