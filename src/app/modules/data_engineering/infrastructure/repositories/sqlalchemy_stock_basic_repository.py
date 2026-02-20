"""股票基础信息 SQLAlchemy 仓储实现。"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.data_engineering.domain.entities.stock_basic import StockBasic
from app.modules.data_engineering.domain.repositories import StockBasicRepository
from app.modules.data_engineering.domain.value_objects.data_source import DataSource
from app.modules.data_engineering.domain.value_objects.stock_status import StockStatus
from app.shared_kernel.infrastructure.sqlalchemy_repository import SqlAlchemyRepository

from ..models.stock_basic_model import StockBasicModel
from .mappers.stock_basic_persistence_mapper import StockBasicPersistenceMapper

# asyncpg 单次查询参数上限 32767（见 https://github.com/MagicStack/asyncpg/issues/251）
# to_row 产出 9 列，留余量取一半：32767 // 9 // 2 ≈ 1819，用 1000 兼顾可读性与往返次数
_ASYNCPG_MAX_PARAMS = 32767
_COLUMNS_PER_ROW = 9
UPSERT_BATCH_SIZE = min(1000, _ASYNCPG_MAX_PARAMS // _COLUMNS_PER_ROW // 2)


class SqlAlchemyStockBasicRepository(
    SqlAlchemyRepository[StockBasic, int | None], StockBasicRepository
):
    """使用 ON CONFLICT (source, third_code) DO UPDATE 的批量 upsert。"""

    def __init__(
        self,
        session: AsyncSession,
        mapper: StockBasicPersistenceMapper | None = None,
    ) -> None:
        super().__init__(session, StockBasicModel)
        self._mapper = mapper or StockBasicPersistenceMapper()

    def _to_entity(self, model: Any) -> StockBasic:
        """ORM Model → 领域聚合根。数据库字符串转回领域枚举。"""
        return StockBasic(
            id=model.id,
            source=DataSource(model.source),
            third_code=model.third_code,
            symbol=model.symbol,
            name=model.name,
            market=model.market,
            area=model.area,
            industry=model.industry,
            list_date=model.list_date,
            status=StockStatus(model.status),
        )

    def _to_model(self, entity: StockBasic) -> Any:
        """领域聚合根 → ORM Model。"""
        row = self._mapper.to_row(entity)
        return StockBasicModel(id=entity.id, **row)

    async def upsert_many(self, stocks: list[StockBasic]) -> None:
        if not stocks:
            return
        now = datetime.now(UTC)
        dialect_name = self._session.get_bind().dialect.name
        for i in range(0, len(stocks), UPSERT_BATCH_SIZE):
            chunk = stocks[i : i + UPSERT_BATCH_SIZE]
            values = [self._mapper.to_row(s) for s in chunk]
            if dialect_name == "postgresql":
                insert_stmt: Any = pg_insert(StockBasicModel).values(values)
            else:
                insert_stmt = sqlite_insert(StockBasicModel).values(values)
            stmt = insert_stmt.on_conflict_do_update(
                index_elements=["source", "third_code"],
                set_={
                    "symbol": insert_stmt.excluded.symbol,
                    "name": insert_stmt.excluded.name,
                    "market": insert_stmt.excluded.market,
                    "area": insert_stmt.excluded.area,
                    "industry": insert_stmt.excluded.industry,
                    "list_date": insert_stmt.excluded.list_date,
                    "status": insert_stmt.excluded.status,
                    "updated_at": now,
                    "version": StockBasicModel.version + 1,
                },
            )
            await self._session.execute(stmt)

    async def find_by_third_codes(self, source: DataSource, third_codes: list[str]) -> list[StockBasic]:
        from sqlalchemy import select
        stmt = select(StockBasicModel).where(
            StockBasicModel.source == source.value,
            StockBasicModel.third_code.in_(third_codes),
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def find_all(self, source: DataSource) -> list[StockBasic]:
        from sqlalchemy import select
        stmt = select(StockBasicModel).where(
            StockBasicModel.source == source.value,
            # StockBasicModel.status == StockStatus.LISTED.value,
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]
