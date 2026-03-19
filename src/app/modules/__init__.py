"""业务模块注册中心。

提供 register_scheduled_tasks() 函数，供应用启动时注册所有模块的定时任务。
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, TypeAlias

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.modules.foundation.application.module_registry import ModuleRegistry

# 定义任务工厂类型
ScheduledTaskFactory: TypeAlias = Callable[
    [],
    tuple[list, dict[str, Callable[[], Awaitable[None]]]],
]


def register_scheduled_tasks(registry: "ModuleRegistry", session_factory: "async_sessionmaker") -> None:
    """注册所有业务模块的定时任务到 ModuleRegistry。

    新增业务模块时，需要在此函数中添加该模块的任务注册代码。

    Args:
        registry: ModuleRegistry 实例。
        session_factory: SQLAlchemy async_sessionmaker 实例。
    """
    # 注册 data_engineering 模块的定时任务
    # 注意：这里使用延迟导入避免循环依赖
    try:
        from app.modules.data_engineering.interfaces.schedulers import create_scheduled_tasks

        # 创建工厂闭包，捕获 session_factory
        def de_factory() -> tuple[list, dict[str, Callable[[], Awaitable[None]]]]:
            return create_scheduled_tasks(session_factory)

        registry.register_scheduled_tasks(de_factory)
    except ImportError:
        # 如果 data_engineering 模块尚未实现任务注册，跳过
        pass

    # 新增模块时，在此处添加注册代码
    # 例如：
    # from app.modules.new_module.interfaces.schedulers import create_scheduled_tasks
    # def new_module_factory() -> tuple[list, dict[str, Callable[[], Awaitable[None]]]]:
    #     return create_scheduled_tasks(session_factory)
    # registry.register_scheduled_tasks(new_module_factory)