"""GetConceptStocks 查询处理器。"""

from app.modules.data_engineering.domain.entities.concept_stock import ConceptStock
from app.modules.data_engineering.domain.exceptions import ConceptNotFoundError
from app.modules.data_engineering.domain.repositories.concept_repository import ConceptRepository
from app.modules.data_engineering.domain.repositories.concept_stock_repository import (
    ConceptStockRepository,
)
from app.shared_kernel.application.query_handler import QueryHandler

from .get_concept_stocks import GetConceptStocks


class GetConceptStocksHandler(QueryHandler[GetConceptStocks, list[ConceptStock]]):
    def __init__(
        self,
        concept_repo: ConceptRepository,
        concept_stock_repo: ConceptStockRepository,
    ) -> None:
        self._concept_repo = concept_repo
        self._concept_stock_repo = concept_stock_repo

    async def handle(self, query: GetConceptStocks) -> list[ConceptStock]:
        concept = await self._concept_repo.find_by_id(query.concept_id)
        if concept is None:
            raise ConceptNotFoundError(f"Concept not found: id={query.concept_id}")
        return await self._concept_stock_repo.find_by_concept_id(query.concept_id)
