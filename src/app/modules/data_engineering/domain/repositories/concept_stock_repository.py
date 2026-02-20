from abc import ABC, abstractmethod

from app.modules.data_engineering.domain.entities.concept_stock import ConceptStock


class ConceptStockRepository(ABC):
    """概念-股票关联仓储接口。不 commit，由调用方 UnitOfWork 管理事务。"""

    @abstractmethod
    async def find_by_concept_id(self, concept_id: int) -> list[ConceptStock]:
        """获取指定概念的所有成分股。"""
        ...

    @abstractmethod
    async def save_many(self, concept_stocks: list[ConceptStock]) -> None:
        """批量保存（新增或更新）。"""
        ...

    @abstractmethod
    async def delete_many(self, concept_stock_ids: list[int]) -> None:
        """批量删除成分股关联。"""
        ...

    @abstractmethod
    async def delete_by_concept_id(self, concept_id: int) -> None:
        """删除指定概念的所有关联关系。"""
        ...
