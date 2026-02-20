"""概念-股票关联实体。"""

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256

from app.shared_kernel.domain.entity import Entity

from ..value_objects.data_source import DataSource


@dataclass(eq=False)
class ConceptStock(Entity[int | None]):
    """概念-股票关联实体。以 (concept_id, source, stock_third_code) 为逻辑唯一键。"""

    id: int | None
    concept_id: int
    source: DataSource
    stock_third_code: str
    stock_symbol: str | None
    content_hash: str
    added_at: datetime

    @staticmethod
    def compute_hash(
        source: DataSource,
        stock_third_code: str,
        stock_symbol: str | None,
    ) -> str:
        content = f"{source.value}|{stock_third_code}|{stock_symbol or ''}"
        return sha256(content.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def calculate_content_hash(
        source: DataSource,
        stock_third_code: str,
        stock_symbol: str | None,
    ) -> str:
        return ConceptStock.compute_hash(source, stock_third_code, stock_symbol)
