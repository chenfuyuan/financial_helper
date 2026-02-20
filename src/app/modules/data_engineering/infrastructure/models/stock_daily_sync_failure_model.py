"""股票日线行情同步失败记录 SQLAlchemy 模型。"""

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.shared_kernel.infrastructure.database import Base


class StockDailySyncFailureModel(Base):
    """表 stock_daily_sync_failure：日线同步失败记录，用于重试与排查。

    Attributes:
        id: 主键，自增。
        source: 数据来源（如 Tushare），存枚举值。
        third_code: 第三方数据源中的股票代码。
        start_date: 本次同步请求的起始日期（含）。
        end_date: 本次同步请求的结束日期（含）。
        error_message: 失败原因或异常信息。
        failed_at: 失败发生时间（含时区）。
        retry_count: 已重试次数。
        resolved: 是否已解决（如重试成功或人工标记）。
        created_at: 创建时间（UTC）。
        updated_at: 最后更新时间（UTC）。
        version: 乐观锁版本号。
    """

    __tablename__ = "stock_daily_sync_failure"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    third_code: Mapped[str] = mapped_column(String(32), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    error_message: Mapped[str] = mapped_column(String, nullable=False)
    failed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
