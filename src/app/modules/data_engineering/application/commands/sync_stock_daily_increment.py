"""增量同步与重试 Command 与 Result。"""

from dataclasses import dataclass
from datetime import date

from app.shared_kernel.application.command import Command


@dataclass(frozen=True)
class SyncIncrementResult:
    trade_date: date
    synced_count: int
    duration_ms: int = 0


@dataclass(frozen=True)
class SyncStockDailyIncrement(Command):
    """增量同步指令。不传 trade_date 则默认昨天自然日。"""

    trade_date: date | None = None


@dataclass(frozen=True)
class RetryResult:
    total: int
    resolved_count: int
    still_failed_count: int
    duration_ms: int = 0


@dataclass(frozen=True)
class RetryStockDailySyncFailures(Command):
    """重试失败记录指令。"""

    max_retries: int = 3
