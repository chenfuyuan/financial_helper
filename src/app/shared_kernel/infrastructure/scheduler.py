"""定时任务调度器抽象：定义任务注册和调度接口，具体实现（APScheduler/Celery Beat 等）后续提供。"""

from abc import ABC, abstractmethod
from collections.abc import Callable, Coroutine
from typing import Any


class Scheduler(ABC):
    """定时任务调度器抽象接口。"""

    @abstractmethod
    def register(
        self,
        name: str,
        cron_expression: str,
        func: Callable[..., Coroutine[Any, Any, None]],
    ) -> None:
        """注册一个定时任务。"""
        ...

    @abstractmethod
    async def start(self) -> None:
        """启动调度器。"""
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        """停止调度器。"""
        ...
