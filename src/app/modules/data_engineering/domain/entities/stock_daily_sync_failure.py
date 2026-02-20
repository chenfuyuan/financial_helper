"""股票日线行情同步失败记录实体。"""

from dataclasses import dataclass
from datetime import date, datetime

from app.shared_kernel.domain.entity import Entity

from ..value_objects.data_source import DataSource


@dataclass(eq=False)
class StockDailySyncFailure(Entity[int | None]):
    """股票日线行情同步失败记录实体。用于记录某只股票某日期区间的同步失败，便于重试与排查。

    Attributes:
        id: 主键；新建未持久化时为 None。
        source: 数据来源（如 Tushare）。
        third_code: 第三方数据源中的股票代码。
        start_date: 本次同步请求的起始日期（含）。
        end_date: 本次同步请求的结束日期（含）。
        error_message: 失败原因或异常信息。
        failed_at: 失败发生时间（含时区）。
        retry_count: 已重试次数。
        resolved: 是否已解决（如重试成功或人工标记）。
    """

    id: int | None
    source: DataSource
    third_code: str
    start_date: date
    end_date: date
    error_message: str
    failed_at: datetime
    retry_count: int
    resolved: bool
