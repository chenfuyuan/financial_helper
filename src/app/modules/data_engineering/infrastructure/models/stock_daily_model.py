"""股票日线行情 SQLAlchemy 模型。"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.shared_kernel.infrastructure.database import Base


class StockDailyModel(Base):
    """表 stock_daily：合并日线、复权因子、每日指标。"""

    __tablename__ = "stock_daily"
    __table_args__ = (
        UniqueConstraint("source", "third_code", "trade_date", name="uq_stock_daily_key"),
    )

    # 字段顺序：id 最前，业务字段居中，公用字段最后
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    third_code: Mapped[str] = mapped_column(String(32), nullable=False)
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

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
