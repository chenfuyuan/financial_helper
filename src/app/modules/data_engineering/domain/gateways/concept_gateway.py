from abc import ABC, abstractmethod

from app.modules.data_engineering.domain.entities.concept import Concept


class ConceptGateway(ABC):
    """从外部数据源拉取概念板块及成分股数据。"""

    @abstractmethod
    async def fetch_concepts(self) -> list[Concept]:
        """获取所有概念板块列表。"""
        ...

    @abstractmethod
    async def fetch_concept_stocks(self, concept_third_code: str, concept_name: str) -> list[tuple[str, str]]:
        """获取指定概念的成分股列表。"""
        ...
