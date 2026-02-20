"""股票日线行情 SQLAlchemy 仓储实现。"""

from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.data_engineering.domain.entities.stock_daily import StockDaily
from app.modules.data_engineering.domain.repositories.stock_daily_repository import (
    StockDailyRepository,
)
from app.modules.data_engineering.domain.value_objects.data_source import DataSource
from app.shared_kernel.infrastructure.sqlalchemy_entity_repository import SqlAlchemyEntityRepository

from ..models.stock_daily_model import StockDailyModel
from .mappers.stock_daily_persistence_mapper import StockDailyPersistenceMapper

UPSERT_BATCH_SIZE = 500


class SqlAlchemyStockDailyRepository(SqlAlchemyEntityRepository[StockDaily, int | None], StockDailyRepository):
    """使用 ON CONFLICT (source, third_code, trade_date) DO UPDATE 的批量 upsert。"""

    def __init__(
        self,
        session: AsyncSession,
        mapper: StockDailyPersistenceMapper | None = None,
    ) -> None:
        super().__init__(session, StockDailyModel)
        self._mapper = mapper or StockDailyPersistenceMapper()

    def _to_entity(self, model: Any) -> StockDaily:
        # 当前暂无查回实体的需求，如有需要再补充
        raise NotImplementedError("Entity conversion not implemented yet")

    def _to_model(self, entity: StockDaily) -> Any:
        return StockDailyModel(id=entity.id, **self._mapper.to_row(entity))

    async def upsert_many(self, records: list[StockDaily]) -> None:
        if not records:
            return
        now = datetime.now(UTC)
        dialect_name = self._session.get_bind().dialect.name

        for i in range(0, len(records), UPSERT_BATCH_SIZE):
            chunk = records[i : i + UPSERT_BATCH_SIZE]
            values = [self._mapper.to_row(r) for r in chunk]

            if dialect_name == "postgresql":
                insert_stmt: Any = pg_insert(StockDailyModel).values(values)
            else:
                insert_stmt = sqlite_insert(StockDailyModel).values(values)

            # 排除唯一键，其它业务字段全部更新
            set_dict = {
                k: getattr(insert_stmt.excluded, k)
                for k in values[0]
                if k not in ("source", "third_code", "trade_date")
            }
            set_dict["updated_at"] = now
            set_dict["version"] = StockDailyModel.version + 1

            stmt = insert_stmt.on_conflict_do_update(
                index_elements=["source", "third_code", "trade_date"],
                set_=set_dict,
            )
            await self._session.execute(stmt)

    async def get_latest_trade_date(self, source: DataSource, third_code: str) -> date | None:
        stmt = (
            select(StockDailyModel.trade_date)
            .where(
                StockDailyModel.source == source.value,
                StockDailyModel.third_code == third_code,
            )
            .order_by(StockDailyModel.trade_date.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
