"""Data Engineering 模块定时任务入口。

提供 create_scheduled_tasks() 函数，供 app.modules 注册定时任务。
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from app.modules.data_engineering.interfaces.schedulers.tasks import (
    create_task_callables,
    get_scheduled_tasks,
)

if TYPE_CHECKING:
    from app.modules.foundation.application.scheduled_task_config import ScheduledTaskConfig


def create_scheduled_tasks(
    session_factory: "async_sessionmaker",
) -> tuple[list["ScheduledTaskConfig"], dict[str, Callable[[], Awaitable[None]]]]:
    """创建 data_engineering 模块的定时任务配置和执行函数。

    这是模块入口函数，返回 (configs, task_callables) 元组，
    供 ModuleRegistry 注册到调度器。

    Args:
        session_factory: SQLAlchemy async_sessionmaker 实例。

    Returns:
        (configs, task_callables) 元组。
    """
    configs = get_scheduled_tasks()
    task_callables = create_task_callables(session_factory)
    return configs, task_callables


__all__ = ["create_scheduled_tasks", "get_scheduled_tasks", "create_task_callables"]
