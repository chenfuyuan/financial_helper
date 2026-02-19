"""StockBasic → 持久化行（dict）映射，供 SQLAlchemy insert 使用。"""

from app.modules.data_engineering.domain.entities.stock_basic import StockBasic
from app.modules.data_engineering.domain.value_objects.data_source import DataSource
from app.modules.data_engineering.domain.value_objects.stock_status import StockStatus


def _source_str(source: DataSource | str) -> str:
    return source.value if isinstance(source, DataSource) else str(source)


def _status_str(status: StockStatus) -> str:
    return status.value


class StockBasicPersistenceMapper:
    """将 StockBasic 转为 upsert 用的 dict（不含 id/created_at/updated_at/version）。"""

    def to_row(self, stock: StockBasic) -> dict:
        """领域实体 → 插入/更新用字典。"""
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
