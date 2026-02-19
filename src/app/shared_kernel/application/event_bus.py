"""EventBus 抽象：领域事件发布与订阅。"""

from abc import ABC, abstractmethod

from app.shared_kernel.domain.domain_event import DomainEvent


class EventBus(ABC):
    """事件总线抽象接口。"""

    @abstractmethod
    async def publish(self, event: DomainEvent) -> None:
        """发布领域事件。"""
        ...
