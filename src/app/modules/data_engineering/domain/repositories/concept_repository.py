from abc import ABC, abstractmethod

from app.modules.data_engineering.domain.entities.concept import Concept
from app.modules.data_engineering.domain.value_objects.data_source import DataSource


class ConceptRepository(ABC):
    """概念板块仓储接口。不 commit，由调用方 UnitOfWork 管理事务。"""

    @abstractmethod
    async def find_all(self, source: DataSource) -> list[Concept]:
        """获取指定数据源的所有概念板块。"""
        ...

    @abstractmethod
    async def find_by_id(self, concept_id: int) -> Concept | None:
        """根据 ID 查找概念板块。"""
        ...

    @abstractmethod
    async def find_by_third_code(self, source: DataSource, third_code: str) -> Concept | None:
        """根据来源和第三方代码查找概念板块。"""
        ...

    @abstractmethod
    async def save(self, concept: Concept) -> Concept:
        """保存概念（新增或更新）。返回含 id 的实体（新增时 DB 分配 id）。"""
        ...

    @abstractmethod
    async def save_many(self, concepts: list[Concept]) -> list[Concept]:
        """批量保存概念（新增或更新）。返回含 id 的实体列表。"""
        ...

    @abstractmethod
    async def delete(self, concept_id: int) -> None:
        """删除指定概念。"""
        ...

    @abstractmethod
    async def delete_many(self, concept_ids: list[int]) -> None:
        """批量删除概念。"""
        ...
