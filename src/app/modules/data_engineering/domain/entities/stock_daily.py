"""股票日线行情实体。"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.shared_kernel.domain.entity import Entity

from ..value_objects.data_source import DataSource


@dataclass(eq=False)
class StockDaily(Entity[int | None]):
    """股票日线行情实体。包含 daily, adj_factor, daily_basic 三个接口的合并数据。

    (source, third_code, trade_date) 为逻辑唯一键。仅包含业务属性，不包含审计字段。

    Attributes:
        id: 主键；新建未持久化时为 None。
        source: 数据来源（如 Tushare）。
        third_code: 第三方数据源中的股票代码。
        symbol: 股票标准代码标识符。
        trade_date: 交易日期。
        open: 开盘价。
        high: 最高价。
        low: 最低价。
        close: 收盘价。
        pre_close: 前收盘价。
        change: 涨跌额。
        pct_chg: 涨跌幅（%）。
        vol: 成交量。
        amount: 成交额（元）。
        adj_factor: 复权因子。
        turnover_rate: 换手率（%）。
        turnover_rate_f: 换手率（自由流通股，%）。
        volume_ratio: 量比。
        pe: 市盈率（总市值/净利润）。
        pe_ttm: 市盈率 TTM（滚动）。
        pb: 市净率。
        ps: 市销率。
        ps_ttm: 市销率 TTM（滚动）。
        dv_ratio: 股息率。
        dv_ttm: 股息率 TTM（滚动）。
        total_share: 总股本。
        float_share: 流通股本。
        free_share: 自由流通股本。
        total_mv: 总市值（元）。
        circ_mv: 流通市值（元）。
    """

    id: int | None
    source: DataSource
    third_code: str
    symbol: str | None
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
