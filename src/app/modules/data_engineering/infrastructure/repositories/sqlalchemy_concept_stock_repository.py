"""ConceptStock SQLAlchemy 仓储实现。"""

from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.data_engineering.domain.entities.concept_stock import ConceptStock
from app.modules.data_engineering.domain.repositories.concept_stock_repository import (
    ConceptStockRepository,
)
from app.modules.data_engineering.domain.value_objects.data_source import DataSource

from ..models.concept_stock_model import ConceptStockModel


class SqlAlchemyConceptStockRepository(ConceptStockRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_entity(model: ConceptStockModel) -> ConceptStock:
        return ConceptStock(
            id=model.id,
            concept_id=model.concept_id,
            source=DataSource(model.source),
            stock_third_code=model.stock_third_code,
            stock_symbol=model.stock_symbol,
            content_hash=model.content_hash,
            added_at=model.added_at,
        )

    async def find_by_concept_id(self, concept_id: int) -> list[ConceptStock]:
        stmt = select(ConceptStockModel).where(ConceptStockModel.concept_id == concept_id)
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def save_many(self, concept_stocks: list[ConceptStock]) -> None:
        if not concept_stocks:
            return

        now = datetime.now(UTC)
        values = [
            {
                "concept_id": cs.concept_id,
                "source": cs.source.value,
                "stock_third_code": cs.stock_third_code,
                "stock_symbol": cs.stock_symbol,
                "content_hash": cs.content_hash,
                "added_at": cs.added_at,
            }
            for cs in concept_stocks
        ]
        dialect_name = self._session.get_bind().dialect.name
        if dialect_name == "postgresql":
            insert_stmt = pg_insert(ConceptStockModel).values(values)
        else:
            insert_stmt = sqlite_insert(ConceptStockModel).values(values)

        stmt = insert_stmt.on_conflict_do_update(
            index_elements=["concept_id", "source", "stock_third_code"],
            set_={
                "stock_symbol": insert_stmt.excluded.stock_symbol,
                "content_hash": insert_stmt.excluded.content_hash,
                "added_at": insert_stmt.excluded.added_at,
                "updated_at": now,
                "version": ConceptStockModel.version + 1,
            },
        )
        await self._session.execute(stmt)

    async def delete_many(self, concept_stock_ids: list[int]) -> None:
        if not concept_stock_ids:
            return
        stmt = delete(ConceptStockModel).where(ConceptStockModel.id.in_(concept_stock_ids))
        await self._session.execute(stmt)

    async def delete_by_concept_id(self, concept_id: int) -> None:
        stmt = delete(ConceptStockModel).where(ConceptStockModel.concept_id == concept_id)
        await self._session.execute(stmt)
