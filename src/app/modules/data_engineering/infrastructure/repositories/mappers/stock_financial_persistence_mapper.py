"""股票财务指标持久化 Mapper：领域实体 ↔ ORM 字典。"""

from dataclasses import asdict
from dataclasses import fields as dc_fields
from decimal import Decimal

from app.modules.data_engineering.domain.entities.stock_financial import StockFinancial
from app.modules.data_engineering.domain.value_objects.data_source import DataSource
from app.modules.data_engineering.infrastructure.models.stock_financial_model import (
    StockFinancialModel,
)

_SKIP = {"id", "source", "third_code", "symbol", "ann_date", "end_date", "update_flag"}
_NUMERIC_FIELDS = {f.name for f in dc_fields(StockFinancial) if f.name not in _SKIP}


class StockFinancialPersistenceMapper:
    """在领域实体和持久化字典/ORM 模型之间转换。"""

    @staticmethod
    def to_dict(entity: StockFinancial) -> dict:
        """实体 → upsert 用字典（不含 id）。"""
        d = asdict(entity)
        d["source"] = entity.source.value
        d.pop("id", None)
        return d

    @staticmethod
    def to_entity(model: StockFinancialModel) -> StockFinancial:
        """ORM 模型 → 领域实体。"""
        kwargs: dict = {}
        for f in dc_fields(StockFinancial):
            if f.name == "source":
                continue
            raw = getattr(model, f.name)
            if f.name in _NUMERIC_FIELDS and raw is not None:
                kwargs[f.name] = Decimal(str(raw))
            else:
                kwargs[f.name] = raw
        kwargs["id"] = model.id
        kwargs["source"] = DataSource(model.source)
        return StockFinancial(**kwargs)
