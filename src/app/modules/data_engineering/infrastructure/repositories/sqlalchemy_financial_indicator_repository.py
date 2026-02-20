"""财务指标 SQLAlchemy 仓储实现。"""

from datetime import date

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.data_engineering.domain.entities.financial_indicator import FinancialIndicator
from app.modules.data_engineering.domain.repositories.financial_indicator_repository import (
    FinancialIndicatorRepository,
)
from app.modules.data_engineering.domain.value_objects.data_source import DataSource
from app.modules.data_engineering.infrastructure.models.financial_indicator_model import (
    FinancialIndicatorModel,
)
from app.modules.data_engineering.infrastructure.repositories.mappers.financial_indicator_persistence_mapper import (
    FinancialIndicatorPersistenceMapper,
)

CONFLICT_COLS = ["source", "third_code", "end_date"]
BATCH_SIZE = 50  # ~100 cols × 50 rows ≈ 5000 params，低于 asyncpg 32767 上限


class SqlAlchemyFinancialIndicatorRepository(FinancialIndicatorRepository):
    """使用 ON CONFLICT (source, third_code, end_date) DO UPDATE 的批量 upsert。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._mapper = FinancialIndicatorPersistenceMapper()

    async def upsert_many(self, records: list[FinancialIndicator]) -> None:
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

        batch = [
            self._mapper.to_dict(r) for r in deduped
        ]

        # 按 PostgreSQL/SQLite 分批处理
        dialect = self._session.get_bind().dialect.name
        update_cols = {k: v for k, v in batch[0].items() if k not in CONFLICT_COLS}

        if dialect == "postgresql":
            stmt = (
                pg_insert(FinancialIndicatorModel)
                .values(batch)
                .on_conflict_do_update(index_elements=CONFLICT_COLS, set_=update_cols)
            )
        else:
            stmt = (
                sqlite_insert(FinancialIndicatorModel)
                .values(batch)
                .on_conflict_do_update(index_elements=CONFLICT_COLS, set_=update_cols)
            )
        await self._session.execute(stmt)

    async def get_latest_end_date(self, source: DataSource, third_code: str) -> date | None:
        stmt = select(func.max(FinancialIndicatorModel.end_date)).where(
            FinancialIndicatorModel.source == source.value,
            FinancialIndicatorModel.third_code == third_code,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
