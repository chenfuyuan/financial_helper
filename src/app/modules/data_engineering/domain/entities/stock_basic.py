"""股票基础信息聚合根。"""

from dataclasses import dataclass
from datetime import date

from app.shared_kernel.domain.aggregate_root import AggregateRoot

from ..value_objects.data_source import DataSource
from ..value_objects.stock_status import StockStatus


@dataclass(eq=False)
class StockBasic(AggregateRoot[int | None]):
    """股票基础信息聚合根。以 (source, third_code) 为逻辑唯一键，仅含业务属性。

    Attributes:
        id: 主键；新建未持久化时为 None。
        source: 数据来源（如 Tushare）。
        third_code: 第三方数据源中的股票代码。
        symbol: 交易所/展示用代码（如 000001.SZ）。
        name: 股票名称。
        market: 市场类型（如 主板、创业板）。
        area: 所属地区。
        industry: 所属行业。
        list_date: 上市日期。
        status: 上市状态（如 上市、退市）。
    """

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
