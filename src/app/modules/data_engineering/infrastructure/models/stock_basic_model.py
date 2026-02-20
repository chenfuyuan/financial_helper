"""股票基础信息 SQLAlchemy 模型。"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.shared_kernel.infrastructure.database import Base


class StockBasicModel(Base):
    """表 stock_basic：股票基础信息。UNIQUE(source, third_code)。

    Attributes:
        id: 主键，自增。
        source: 数据来源（如 Tushare），存枚举值。
        third_code: 第三方数据源中的股票代码。
        symbol: 交易所/展示用代码（如 000001.SZ）。
        name: 股票名称。
        market: 市场类型（如 主板、创业板）。
        area: 所属地区。
        industry: 所属行业。
        list_date: 上市日期。
        status: 上市状态（如 上市、退市），存枚举值。
        created_at: 创建时间（UTC）。
        updated_at: 最后更新时间（UTC）。
        version: 乐观锁版本号。
    """

    __tablename__ = "stock_basic"
    __table_args__ = (
        UniqueConstraint("source", "third_code", name="uq_stock_basic_source_third_code"),
    )

    # 字段顺序：id 最前，业务字段居中，公用字段最后（便于查询结果查看）
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    third_code: Mapped[str] = mapped_column(String(32), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    market: Mapped[str] = mapped_column(String(32), nullable=False)
    area: Mapped[str] = mapped_column(String(32), nullable=False)
    industry: Mapped[str] = mapped_column(String(64), nullable=False)
    list_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(8), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
