"""GetConcepts 查询处理器。"""

from app.modules.data_engineering.domain.entities.concept import Concept
from app.modules.data_engineering.domain.repositories.concept_repository import ConceptRepository
from app.modules.data_engineering.domain.value_objects.data_source import DataSource
from app.shared_kernel.application.query_handler import QueryHandler

from .get_concepts import GetConcepts


class GetConceptsHandler(QueryHandler[GetConcepts, list[Concept]]):
    def __init__(self, concept_repo: ConceptRepository) -> None:
        self._concept_repo = concept_repo

    async def handle(self, query: GetConcepts) -> list[Concept]:
        source = query.source or DataSource.AKSHARE
        return await self._concept_repo.find_all(source)
