"""基于 APScheduler 的 AsyncIOScheduler 实现。

提供 AsyncIOSchedulerImpl 类，实现 Scheduler Protocol。
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger as APSchedulerCronTrigger

from app.modules.foundation.application.scheduled_task_config import ScheduledTaskConfig
from app.modules.foundation.application.scheduler import Scheduler
from app.shared_kernel.infrastructure.logging import get_logger

logger = get_logger(__name__)


class AsyncIOSchedulerImpl(Scheduler):
    """基于 APScheduler AsyncIOScheduler 的调度器实现。

    使用内存 Job Store，支持 cron 触发器，提供详细的结构化日志记录。

    Attributes:
        _scheduler: APScheduler AsyncIOScheduler 实例。
    """

    def __init__(self) -> None:
        """初始化调度器，创建 AsyncIOScheduler 实例（使用内存 Job Store）。"""
        self._scheduler = AsyncIOScheduler()

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
        # 创建 APScheduler CronTrigger
        trigger_kwargs = config.trigger.to_cron_kwargs()
        trigger = APSchedulerCronTrigger(**trigger_kwargs)

        # 包装任务以添加日志记录
        wrapped_callable = self._wrap_task_with_logging(config, task_callable)

        self._scheduler.add_job(
            wrapped_callable,
            trigger=trigger,
            id=config.id,
            name=config.name,
            max_instances=config.max_instances,
            coalesce=config.coalesce,
            misfire_grace_time=config.misfire_grace_time,
        )

        logger.info(
            "Task registered",
            task_id=config.id,
            task_name=config.name,
            module=config.module,
        )

    def start(self) -> None:
        """启动调度器，开始触发已注册的任务。"""
        self._scheduler.start()
        logger.info("Scheduler started")

    def shutdown(self, wait: bool = True) -> None:
        """关闭调度器。

        Args:
            wait: 是否等待正在执行的任务完成。
        """
        self._scheduler.shutdown(wait=wait)
        logger.info("Scheduler shut down", wait=wait)

    def _wrap_task_with_logging(
        self,
        config: ScheduledTaskConfig,
        task_callable: Callable[[], Awaitable[None]],
    ) -> Callable[[], Awaitable[None]]:
        """包装任务函数以添加日志记录和耗时统计。

        Args:
            config: 任务配置。
            task_callable: 原始任务执行函数。

        Returns:
            包装后的任务执行函数。
        """

        async def wrapped_task() -> None:
            start_time = time.perf_counter()
            logger.info(
                "Task started",
                task_id=config.id,
                task_name=config.name,
                module=config.module,
            )
            try:
                await task_callable()
                duration_ms = int((time.perf_counter() - start_time) * 1000)
                logger.info(
                    "Task completed",
                    task_id=config.id,
                    task_name=config.name,
                    module=config.module,
                    duration_ms=duration_ms,
                )
            except Exception as e:
                duration_ms = int((time.perf_counter() - start_time) * 1000)
                logger.error(
                    "Task failed",
                    task_id=config.id,
                    task_name=config.name,
                    module=config.module,
                    duration_ms=duration_ms,
                    error=str(e),
                    exc_info=True,
                )
                raise

        return wrapped_task
