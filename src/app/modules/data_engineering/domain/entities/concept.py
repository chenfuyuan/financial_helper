"""概念板块聚合根。"""

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256

from app.shared_kernel.domain.aggregate_root import AggregateRoot

from ..value_objects.data_source import DataSource


@dataclass(eq=False)
class Concept(AggregateRoot[int | None]):
    """概念板块聚合根。以 (source, third_code) 为逻辑唯一键，仅含业务属性。"""

    id: int | None
    source: DataSource
    third_code: str
    name: str
    content_hash: str
    last_synced_at: datetime

    @staticmethod
    def compute_hash(source: DataSource, third_code: str, name: str) -> str:
        content = f"{source.value}|{third_code}|{name}"
        return sha256(content.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def calculate_content_hash(source: DataSource, third_code: str, name: str) -> str:
        return Concept.compute_hash(source, third_code, name)
