"""股票日线行情实体。"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.shared_kernel.domain.entity import Entity

from ..value_objects.data_source import DataSource


@dataclass(eq=False)
class StockDaily(Entity[int | None]):
    """股票日线行情实体。包含 daily, adj_factor, daily_basic 三个接口的合并数据。
    
    (source, third_code, trade_date) 为逻辑唯一键。
    仅包含业务属性，不包含审计字段。
    """

    id: int | None
    source: DataSource
    third_code: str
    trade_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    pre_close: Decimal
    change: Decimal
    pct_chg: Decimal
    vol: Decimal
    amount: Decimal
    adj_factor: Decimal
    turnover_rate: Decimal | None
    turnover_rate_f: Decimal | None
    volume_ratio: Decimal | None
    pe: Decimal | None
    pe_ttm: Decimal | None
    pb: Decimal | None
    ps: Decimal | None
    ps_ttm: Decimal | None
    dv_ratio: Decimal | None
    dv_ttm: Decimal | None
    total_share: Decimal | None
    float_share: Decimal | None
    free_share: Decimal | None
    total_mv: Decimal | None
    circ_mv: Decimal | None
