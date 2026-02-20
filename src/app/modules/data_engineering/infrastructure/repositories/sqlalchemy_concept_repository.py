"""Concept SQLAlchemy 仓储实现。"""


from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.data_engineering.domain.entities.concept import Concept
from app.modules.data_engineering.domain.repositories.concept_repository import ConceptRepository
from app.modules.data_engineering.domain.value_objects.data_source import DataSource

from ..models.concept_model import ConceptModel


class SqlAlchemyConceptRepository(ConceptRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_entity(model: ConceptModel) -> Concept:
        return Concept(
            id=model.id,
            source=DataSource(model.source),
            third_code=model.third_code,
            name=model.name,
            content_hash=model.content_hash,
            last_synced_at=model.last_synced_at,
        )

    async def find_all(self, source: DataSource) -> list[Concept]:
        stmt = (
            select(ConceptModel)
            .where(ConceptModel.source == source.value)
            .order_by(ConceptModel.id.asc())
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def find_by_id(self, concept_id: int) -> Concept | None:
        model = await self._session.get(ConceptModel, concept_id)
        if model is None:
            return None
        return self._to_entity(model)

    async def find_by_third_code(self, source: DataSource, third_code: str) -> Concept | None:
        stmt = select(ConceptModel).where(
            ConceptModel.source == source.value,
            ConceptModel.third_code == third_code,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._to_entity(model)

    async def save(self, concept: Concept) -> Concept:
        existing: ConceptModel | None = None
        if concept.id is not None:
            existing = await self._session.get(ConceptModel, concept.id)
        if existing is None:
            stmt = select(ConceptModel).where(
                ConceptModel.source == concept.source.value,
                ConceptModel.third_code == concept.third_code,
            )
            result = await self._session.execute(stmt)
            existing = result.scalar_one_or_none()

        if existing is None:
            model = ConceptModel(
                source=concept.source.value,
                third_code=concept.third_code,
                name=concept.name,
                content_hash=concept.content_hash,
                last_synced_at=concept.last_synced_at,
            )
            self._session.add(model)
            await self._session.flush()
            return self._to_entity(model)

        existing.name = concept.name
        existing.content_hash = concept.content_hash
        existing.last_synced_at = concept.last_synced_at
        existing.version = existing.version + 1
        await self._session.flush()
        return self._to_entity(existing)

    async def delete(self, concept_id: int) -> None:
        model = await self._session.get(ConceptModel, concept_id)
        if model is not None:
            await self._session.delete(model)

    async def delete_many(self, concept_ids: list[int]) -> None:
        if not concept_ids:
            return
        stmt = delete(ConceptModel).where(ConceptModel.id.in_(concept_ids))
        await self._session.execute(stmt)
