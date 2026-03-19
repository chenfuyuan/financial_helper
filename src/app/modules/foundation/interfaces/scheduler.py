"""调度器依赖注入入口。

提供 get_scheduler() 函数，用于在 interfaces 层获取调度器实例。
"""

from __future__ import annotations

from app.modules.foundation.application.scheduler import Scheduler
from app.modules.foundation.infrastructure.asyncio_scheduler_impl import AsyncIOSchedulerImpl


def get_scheduler() -> Scheduler:
    """获取调度器实例。

    返回 Scheduler Protocol 类型（不暴露具体实现），
    用于在 FastAPI 的 interfaces 层通过依赖注入获取调度器实例。

    Returns:
        Scheduler Protocol 类型的调度器实例。
    """
    return AsyncIOSchedulerImpl()
