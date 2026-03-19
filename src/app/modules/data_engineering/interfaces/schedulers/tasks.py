"""Data Engineering 模块定时任务定义。

提供股票日线增量同步定时任务，每天 16:30 执行。
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from app.config import settings
from app.modules.foundation.application.scheduled_task_config import CronTrigger, ScheduledTaskConfig
from app.modules.data_engineering.application.commands.sync_stock_daily_increment import (
    SyncStockDailyIncrement,
)
from app.modules.data_engineering.infrastructure import (
    SqlAlchemyStockBasicRepository,
    SqlAlchemyStockDailyRepository,
    TuShareStockDailyGateway,
)
from app.shared_kernel.infrastructure.logging import get_logger
from app.shared_kernel.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import async_sessionmaker

logger = get_logger(__name__)


def get_scheduled_tasks() -> list[ScheduledTaskConfig]:
    """获取 data_engineering 模块的定时任务配置列表。

    Returns:
        任务配置列表。
    """
    return [
        ScheduledTaskConfig(
            id="de.sync_stock_daily_increment",
            trigger=CronTrigger(hour=16, minute=30),
            name="同步股票日线增量",
            module="data_engineering",
            max_instances=1,
            coalesce=True,
            misfire_grace_time=7200,
        ),
    ]


def create_task_callables(
    session_factory: async_sessionmaker,
) -> dict[str, Callable[[], Awaitable[None]]]:
    """创建任务执行函数映射。

    任务执行函数自行管理 Session 生命周期：
    创建 session → 构造 Handler → 执行 command → 关闭 session。

    Args:
        session_factory: SQLAlchemy async_sessionmaker 实例。

    Returns:
        任务 ID 到 async callable 的映射。
    """
    async def sync_stock_daily_increment() -> None:
        """同步股票日线增量数据。

        任务执行函数自行管理 Session 生命周期，不通过 Mediator 分发。
        """
        async with session_factory() as session:
            uow = SqlAlchemyUnitOfWork(session)
            gateway = TuShareStockDailyGateway(token=settings.TUSHARE_TOKEN)
            daily_repo = SqlAlchemyStockDailyRepository(session)
            basic_repo = SqlAlchemyStockBasicRepository(session)

            # 直接构造 Handler，避免 Mediator 与 session 管理的耦合
            from app.modules.data_engineering.application.commands import SyncStockDailyIncrementHandler

            handler = SyncStockDailyIncrementHandler(
                gateway=gateway,
                daily_repo=daily_repo,
                basic_repo=basic_repo,
                uow=uow,
            )

            command = SyncStockDailyIncrement()
            result = await handler.handle(command)
            logger.info(
                "Scheduled task completed",
                task_id="de.sync_stock_daily_increment",
                synced_count=result.synced_count,
            )

    return {
        "de.sync_stock_daily_increment": sync_stock_daily_increment,
    }
