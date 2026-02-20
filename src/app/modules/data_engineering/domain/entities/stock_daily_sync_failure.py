"""股票日线行情同步失败记录实体。"""

from dataclasses import dataclass
from datetime import date, datetime

from app.shared_kernel.domain.entity import Entity

from ..value_objects.data_source import DataSource


@dataclass(eq=False)
class StockDailySyncFailure(Entity[int | None]):
    """股票日线行情同步失败记录实体。"""

    id: int | None
    source: DataSource
    third_code: str
    start_date: date
    end_date: date
    error_message: str
    failed_at: datetime
    retry_count: int
    resolved: bool
