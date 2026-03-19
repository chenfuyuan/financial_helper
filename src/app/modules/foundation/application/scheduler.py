"""调度器抽象接口。

定义 Scheduler Protocol，作为调度器的基本操作契约。
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Protocol, runtime_checkable

from app.modules.foundation.application.scheduled_task_config import ScheduledTaskConfig


@runtime_checkable
class Scheduler(Protocol):
    """调度器抽象接口，定义调度器的基本操作契约。

    Scheduler Protocol 定义了调度器的核心方法，包括添加任务、启动和关闭。
    具体实现（如 AsyncIOSchedulerImpl）需要实现这些方法。

    Methods:
        add_job: 添加定时任务到调度器。
        start: 启动调度器。
        shutdown: 关闭调度器。
    """

    def add_job(
        self,
        config: ScheduledTaskConfig,
        task_callable: Callable[[], Awaitable[None]],
    ) -> None:
        """添加定时任务到调度器。

        Args:
            config: 任务配置，包含触发器、任务 ID 等信息。
            task_callable: 任务执行函数，无参数 async callable。
        """
        ...

    def start(self) -> None:
        """启动调度器，开始触发已注册的任务。"""
        ...

    def shutdown(self, wait: bool = True) -> None:
        """关闭调度器。

        Args:
            wait: 是否等待正在执行的任务完成。
        """
        ...
