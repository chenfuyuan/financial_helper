"""股票基础信息领域实体与枚举。"""

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from app.shared_kernel.domain.entity import Entity


class StockStatus(StrEnum):
    """上市状态。"""

    LISTED = "L"
    DELISTED = "D"
    SUSPENDED = "P"


class DataSource(StrEnum):
    """数据来源。"""

    TUSHARE = "TUSHARE"


@dataclass(eq=False)
class StockBasic(Entity[int | None]):
    """股票基础信息实体。含基础字段与业务字段，以 (source, third_code) 为逻辑唯一键。"""

    id: int | None
    created_at: datetime
    updated_at: datetime
    version: int
    source: DataSource | str
    third_code: str
    symbol: str
    name: str
    market: str
    area: str
    industry: str
    list_date: date
    status: StockStatus
