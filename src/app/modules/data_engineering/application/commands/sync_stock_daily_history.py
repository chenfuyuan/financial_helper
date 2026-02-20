"""历史同步 Command 与 Result。"""

from dataclasses import dataclass

from app.shared_kernel.application.command import Command


@dataclass(frozen=True)
class SyncHistoryResult:
    total: int
    success_count: int
    failure_count: int
    synced_days: int


@dataclass(frozen=True)
class SyncStockDailyHistory(Command):
    """历史同步指令。不传 ts_codes 则全量同步。"""

    ts_codes: list[str] | None = None
