"""查询指定概念成分股。"""

from dataclasses import dataclass

from app.shared_kernel.application.query import Query


@dataclass(frozen=True)
class GetConceptStocks(Query):
    concept_id: int
