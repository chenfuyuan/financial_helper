"""缓存客户端抽象：定义统一的缓存接口，具体实现（Redis 等）在模块或全局基础设施层提供。"""

from abc import ABC, abstractmethod
from typing import Any


class CacheClient(ABC):
    """缓存客户端抽象接口。"""

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """获取缓存值，不存在返回 None。"""
        ...

    @abstractmethod
    async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        """设置缓存值，可选 TTL。"""
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """删除缓存键。"""
        ...
