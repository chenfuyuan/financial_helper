"""查询概念板块列表。"""

from dataclasses import dataclass

from app.modules.data_engineering.domain.value_objects.data_source import DataSource
from app.shared_kernel.application.query import Query


@dataclass(frozen=True)
class GetConcepts(Query):
    source: DataSource | None = None
