"""StockDailySyncFailure SQLAlchemy 仓储实现。"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.data_engineering.domain.entities.stock_daily_sync_failure import (
    StockDailySyncFailure,
)
from app.modules.data_engineering.domain.repositories.stock_daily_sync_failure_repository import (
    StockDailySyncFailureRepository,
)
from app.modules.data_engineering.domain.value_objects.data_source import DataSource
from app.shared_kernel.infrastructure.sqlalchemy_entity_repository import SqlAlchemyEntityRepository

from ..models.stock_daily_sync_failure_model import StockDailySyncFailureModel


class SqlAlchemyStockDailySyncFailureRepository(
    SqlAlchemyEntityRepository[StockDailySyncFailure, int | None], StockDailySyncFailureRepository
):
    """失败记录仓储实现。"""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, StockDailySyncFailureModel)

    def _to_entity(self, model: Any) -> StockDailySyncFailure:
        return StockDailySyncFailure(
            id=model.id,
            source=DataSource(model.source),
            third_code=model.third_code,
            start_date=model.start_date,
            end_date=model.end_date,
            error_message=model.error_message,
            failed_at=model.failed_at,
            retry_count=model.retry_count,
            resolved=model.resolved,
        )

    def _to_model(self, entity: StockDailySyncFailure) -> Any:
        return StockDailySyncFailureModel(
            id=entity.id,
            source=entity.source.value,
            third_code=entity.third_code,
            start_date=entity.start_date,
            end_date=entity.end_date,
            error_message=entity.error_message,
            failed_at=entity.failed_at,
            retry_count=entity.retry_count,
            resolved=entity.resolved,
        )

    async def save(self, failure: StockDailySyncFailure) -> None:
        model = self._to_model(failure)
        if model.id is None:
            self._session.add(model)
        else:
            await self._session.merge(model)

    async def find_unresolved(self, max_retries: int = 3) -> list[StockDailySyncFailure]:
        stmt = (
            select(StockDailySyncFailureModel)
            .where(
                StockDailySyncFailureModel.resolved == False,  # noqa: E712
                StockDailySyncFailureModel.retry_count < max_retries,
            )
            .order_by(StockDailySyncFailureModel.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def mark_resolved(self, failure_id: int) -> None:
        if failure_id is None:
            return
        model = await self._session.get(StockDailySyncFailureModel, failure_id)
        if model:
            model.resolved = True
