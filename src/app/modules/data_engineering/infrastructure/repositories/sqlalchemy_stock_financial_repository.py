"""股票财务指标 SQLAlchemy 仓储实现。"""

from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.data_engineering.domain.entities.stock_financial import StockFinancial
from app.modules.data_engineering.domain.repositories.stock_financial_repository import (
    StockFinancialRepository,
)
from app.modules.data_engineering.domain.value_objects.data_source import DataSource
from app.modules.data_engineering.infrastructure.models.stock_financial_model import (
    StockFinancialModel,
)
from app.modules.data_engineering.infrastructure.repositories.mappers.stock_financial_persistence_mapper import (
    StockFinancialPersistenceMapper,
)

CONFLICT_COLS = ["source", "third_code", "end_date"]
BATCH_SIZE = 50  # ~100 cols × 50 rows ≈ 5000 params，低于 asyncpg 32767 上限


class SqlAlchemyStockFinancialRepository(StockFinancialRepository):
    """使用 ON CONFLICT (source, third_code, end_date) DO UPDATE 的批量 upsert。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._mapper = StockFinancialPersistenceMapper()

    async def upsert_many(self, records: list[StockFinancial]) -> None:
        if not records:
            return

        # 按唯一键去重：保留最后一条（最新数据）
        seen = set()
        deduped = []
        for r in records:
            key = (r.source.value, r.third_code, r.end_date)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(r)

        batch = [self._mapper.to_dict(r) for r in deduped]

        # 按 PostgreSQL/SQLite 分批处理
        dialect = self._session.get_bind().dialect.name
        update_cols = {k: v for k, v in batch[0].items() if k not in CONFLICT_COLS}

        if dialect == "postgresql":
            pg_stmt: Any = (
                pg_insert(StockFinancialModel)
                .values(batch)
                .on_conflict_do_update(index_elements=CONFLICT_COLS, set_=update_cols)
            )
        else:
            sqlite_stmt: Any = (
                sqlite_insert(StockFinancialModel)
                .values(batch)
                .on_conflict_do_update(index_elements=CONFLICT_COLS, set_=update_cols)
            )
        await self._session.execute(pg_stmt if dialect == "postgresql" else sqlite_stmt)

    async def get_latest_end_date(self, source: DataSource, third_code: str) -> date | None:
        stmt = select(func.max(StockFinancialModel.end_date)).where(
            StockFinancialModel.source == source.value,
            StockFinancialModel.third_code == third_code,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
