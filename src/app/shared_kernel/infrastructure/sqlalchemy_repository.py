from abc import abstractmethod
from typing import Any, Protocol, TypeVar

from sqlalchemy import select
from sqlalchemy.engine import Result
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared_kernel.domain.aggregate_root import AggregateRoot
from app.shared_kernel.domain.repository import Repository

AR = TypeVar("AR", bound=AggregateRoot)
ID = TypeVar("ID")


class _ModelWithId(Protocol):
    id: Any


class SqlAlchemyRepository(Repository[AR, ID]):
    def __init__(self, session: AsyncSession, model_class: type[_ModelWithId]) -> None:
        self._session = session
        self._model_class = model_class

    @abstractmethod
    def _to_entity(self, model: Any) -> AR:
        pass

    @abstractmethod
    def _to_model(self, entity: AR) -> Any:
        pass

    async def save(self, aggregate: AR) -> None:
        model = self._to_model(aggregate)
        self._session.add(model)

    async def find_by_id(self, id: ID) -> AR | None:
        result: Result[Any] = await self._session.execute(
            select(self._model_class).where(self._model_class.id == id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def delete(self, aggregate: AR) -> None:
        model = await self._session.get(self._model_class, aggregate.id)
        if model:
            await self._session.delete(model)
        return None
