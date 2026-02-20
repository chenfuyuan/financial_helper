"""Entity专用的SQLAlchemy仓储基类，用于非聚合根的实体。"""

from abc import abstractmethod
from typing import Any, Generic, Protocol, TypeVar

from sqlalchemy import select
from sqlalchemy.engine import Result
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared_kernel.domain.entity import Entity

E = TypeVar("E", bound=Entity[Any])
EntityID = TypeVar("EntityID", bound=Any)


class _ModelWithId(Protocol):
    id: Any


class SqlAlchemyEntityRepository(Generic[E, EntityID]):
    """Entity专用的SQLAlchemy仓储基类。"""

    def __init__(self, session: AsyncSession, model_class: type[_ModelWithId]) -> None:
        self._session = session
        self._model_class = model_class

    @abstractmethod
    def _to_entity(self, model: Any) -> E:
        pass

    @abstractmethod
    def _to_model(self, entity: E) -> Any:
        pass

    async def save(self, entity: E) -> None:
        model = self._to_model(entity)
        self._session.add(model)

    async def find_by_id(self, id: EntityID) -> E | None:
        result: Result[Any] = await self._session.execute(select(self._model_class).where(self._model_class.id == id))
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def delete(self, entity: E) -> None:
        model = await self._session.get(self._model_class, entity.id)
        if model:
            await self._session.delete(model)
        return None
