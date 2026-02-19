"""消息总线抽象：定义异步消息发布接口，具体实现（Celery/RabbitMQ 等）后续提供。"""

from abc import ABC, abstractmethod
from typing import Any


class MessageBus(ABC):
    """异步消息总线抽象接口。"""

    @abstractmethod
    async def publish(self, topic: str, payload: dict[str, Any]) -> None:
        """发布消息到指定主题。"""
        ...
