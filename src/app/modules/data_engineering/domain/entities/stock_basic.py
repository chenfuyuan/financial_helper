"""股票基础信息聚合根。"""

from dataclasses import dataclass
from datetime import date

from app.shared_kernel.domain.aggregate_root import AggregateRoot

from ..value_objects.data_source import DataSource
from ..value_objects.stock_status import StockStatus


@dataclass(eq=False)
class StockBasic(AggregateRoot[int | None]):
    """股票基础信息聚合根。以 (source, third_code) 为逻辑唯一键，仅含业务属性。"""

    id: int | None
    source: DataSource
    third_code: str
    symbol: str
    name: str
    market: str
    area: str
    industry: str
    list_date: date
    status: StockStatus
