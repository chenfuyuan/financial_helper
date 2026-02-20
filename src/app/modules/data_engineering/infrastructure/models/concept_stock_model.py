"""概念-股票关联 SQLAlchemy 模型。"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.shared_kernel.infrastructure.database import Base


class ConceptStockModel(Base):
    """表 concept_stock。UNIQUE(concept_id, source, stock_third_code)。"""

    __tablename__ = "concept_stock"
    __table_args__ = (
        UniqueConstraint("concept_id", "source", "stock_third_code", name="uq_concept_stock_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    concept_id: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    stock_third_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    stock_symbol: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    content_hash: Mapped[str] = mapped_column(String(16), nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
