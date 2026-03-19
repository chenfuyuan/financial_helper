"""模块注册器，用于业务模块注册定时任务。

提供 ModuleRegistry 类，允许业务模块主动注册定时任务工厂，
foundation 不依赖具体业务模块。
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, TypeAlias

from app.shared_kernel.infrastructure.logging import get_logger

if TYPE_CHECKING:
    from app.modules.foundation.application.scheduler import Scheduler
    from app.modules.foundation.application.scheduled_task_config import ScheduledTaskConfig

# 定义任务工厂类型：返回 (configs, task_callables) 元组
ScheduledTaskFactory: TypeAlias = Callable[
    [],
    tuple[list["ScheduledTaskConfig"], dict[str, Callable[[], Awaitable[None]]]],
]

logger = get_logger(__name__)


class ModuleRegistry:
    """模块注册器，管理业务模块的定时任务注册。

    业务模块通过 `register_scheduled_tasks()` 方法注册任务工厂，
    应用启动时调用 `register_all_to_scheduler()` 将所有任务注册到调度器。

    使用实例变量存储状态，确保不同实例之间状态隔离。

    Attributes:
        _scheduled_task_factories: 已注册的任务工厂列表。
    """

    def __init__(self) -> None:
        """初始化模块注册器。"""
        self._scheduled_task_factories: list[ScheduledTaskFactory] = []

    def register_scheduled_tasks(self, factory: ScheduledTaskFactory) -> None:
        """注册任务工厂。

        Args:
            factory: 任务工厂函数，返回 (configs, task_callables) 元组。
        """
        self._scheduled_task_factories.append(factory)
        logger.debug("Task factory registered", factory=factory.__name__)

    def register_all_to_scheduler(self, scheduler: "Scheduler") -> None:
        """将所有已注册的任务注册到调度器。

        Args:
            scheduler: 调度器实例。

        Raises:
            ValueError: 当任务配置没有对应的 callable 时抛出。
        """
        for factory in self._scheduled_task_factories:
            configs, task_callables = factory()
            self._validate_tasks(configs, task_callables, factory.__name__)

            for config in configs:
                task_callable = task_callables[config.id]
                scheduler.add_job(config, task_callable)
                logger.info(
                    "Task registered to scheduler",
                    task_id=config.id,
                    module=config.module,
                )

    def _validate_tasks(
        self,
        configs: list["ScheduledTaskConfig"],
        task_callables: dict[str, Callable[[], Awaitable[None]]],
        factory_name: str,
    ) -> None:
        """验证任务配置和 callable 的完整性。

        Args:
            configs: 任务配置列表。
            task_callables: 任务 ID 到 callable 的映射。
            factory_name: 工厂名称（用于错误信息）。

        Raises:
            ValueError: 当任务配置没有对应的 callable 时抛出。
        """
        for config in configs:
            if config.id not in task_callables:
                raise ValueError(
                    f"Task callable not found for config.id='{config.id}', "
                    f"module='{config.module}', factory='{factory_name}'"
                )
