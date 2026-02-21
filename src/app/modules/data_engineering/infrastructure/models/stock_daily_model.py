"""股票日线行情 SQLAlchemy 模型。"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.shared_kernel.infrastructure.database import Base


class StockDailyModel(Base):
    """表 stock_daily：日线行情，合并日线、复权因子、每日指标。
    UNIQUE(source, third_code, trade_date)。
    """

    """Attributes:
        id: 主键，自增。
        source: 数据来源（如 Tushare），存枚举值。
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
        pe: 市盈率。
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
        created_at: 创建时间（UTC）。
        updated_at: 最后更新时间（UTC）。
        version: 乐观锁版本号。
    """

    __tablename__ = "stock_daily"
    __table_args__ = (UniqueConstraint("source", "third_code", "trade_date", name="uq_stock_daily_key"),)

    # 字段顺序：id 最前，业务字段居中，公用字段最后
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    third_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    symbol: Mapped[str | None] = mapped_column(String(32), nullable=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    open: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False)
    high: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False)
    low: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False)
    close: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False)
    pre_close: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False)
    change: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False)
    pct_chg: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False)
    vol: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(20, 4), nullable=False)

    adj_factor: Mapped[float] = mapped_column(Numeric(20, 6), nullable=False)

    turnover_rate: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    turnover_rate_f: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    volume_ratio: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    pe: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    pe_ttm: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    pb: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    ps: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    ps_ttm: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    dv_ratio: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    dv_ttm: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    total_share: Mapped[float | None] = mapped_column(Numeric(24, 4), nullable=True)
    float_share: Mapped[float | None] = mapped_column(Numeric(24, 4), nullable=True)
    free_share: Mapped[float | None] = mapped_column(Numeric(24, 4), nullable=True)
    total_mv: Mapped[float | None] = mapped_column(Numeric(24, 4), nullable=True)
    circ_mv: Mapped[float | None] = mapped_column(Numeric(24, 4), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
