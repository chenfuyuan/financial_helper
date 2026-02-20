"""财务指标同步 Command 与 Result。"""

from dataclasses import dataclass, field

from app.shared_kernel.application.command import Command


@dataclass(frozen=True)
class SyncFinanceIndicatorFull(Command):
    """全量同步财务指标。ts_codes 为空则同步全市场。"""

    ts_codes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SyncFinanceIndicatorByStock(Command):
    """同步单只股票的财务指标。"""

    ts_code: str


@dataclass(frozen=True)
class SyncFinanceIndicatorIncrement(Command):
    """增量同步财务指标（断点续传）。ts_codes 为空则同步全市场。"""

    ts_codes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SyncFinanceIndicatorResult:
    """财务指标同步结果。"""

    total: int
    success_count: int
    failure_count: int
    synced_records: int
