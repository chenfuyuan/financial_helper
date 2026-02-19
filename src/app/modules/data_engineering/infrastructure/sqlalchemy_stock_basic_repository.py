"""股票基础信息 SQLAlchemy 仓储实现。"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.data_engineering.domain.stock_basic import DataSource, StockBasic, StockStatus
from app.modules.data_engineering.domain.stock_basic_repository import StockBasicRepository

from .models.stock_basic_model import StockBasicModel


def _source_str(source: DataSource | str) -> str:
    return source.value if isinstance(source, DataSource) else str(source)


def _status_str(status: StockStatus) -> str:
    return status.value


def _to_model(stock: StockBasic) -> dict:
    return {
        "source": _source_str(stock.source),
        "third_code": stock.third_code,
        "symbol": stock.symbol,
        "name": stock.name,
        "market": stock.market,
        "area": stock.area,
        "industry": stock.industry,
        "list_date": stock.list_date,
        "status": _status_str(stock.status),
    }


class SqlAlchemyStockBasicRepository(StockBasicRepository):
    """使用 ON CONFLICT (source, third_code) DO UPDATE 的批量 upsert。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_many(self, stocks: list[StockBasic]) -> None:
        if not stocks:
            return
        now = datetime.now(UTC)
        values = [_to_model(s) for s in stocks]
        dialect_name = self._session.get_bind().dialect.name
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
