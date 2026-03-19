# Foundation 调度器设计文档

**日期:** 2026-02-24  
**状态:** 已批准  
**类型:** 基础设施层新功能

---

## 1. 概述

为 foundation 模块引入定时任务调度器，供其他业务模块（如 data_engineering）使用，实现定时执行数据同步等任务。

**关键设计约束：**
- 定时任务无 HTTP Request 上下文，需自行管理 Session/UoW 生命周期
- 任务直接构造 Handler 并调用，不通过 Mediator 分发
- foundation 不依赖任何业务模块

---

## 2. 核心决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 调度器类型 | APScheduler（AsyncIOScheduler） | 轻量级、支持 async、单机够用 |
| 持久化 | 不持久化（内存 Job Store）+ 预留接口 | 任务是静态的，重启后重新注册即可 |
| 错误处理 | 失败后告警（日志），不自动重试 | 数据同步任务需要人工确认，避免脏数据 |
| 日志记录 | 详细结构化日志（含耗时） | 任务开始/结束/参数/异常/耗时全部记录 |
| 任务注册 | 手动注册 + 模块工厂模式 | 依赖方向正确，符合现有架构 |
| 依赖方向 | 业务模块主动注册到 foundation | foundation 不依赖具体业务模块 |
| Session 管理 | 任务自行创建 session，独立于 HTTP 请求 | 无 Request 上下文，需独立 session 生命周期 |
| 任务执行路径 | 直接构造 Handler，不走 Mediator | Mediator 未注册 handler factory，避免耦合 |

---

## 3. 架构设计

### 3.1 分层结构

```
foundation 模块（src/app/foundation/）
├── __init__.py
├── application/
│   ├── __init__.py
│   └── scheduler.py              # Scheduler Protocol + ScheduledTaskConfig + CronTrigger
├── infrastructure/
│   ├── __init__.py
│   └── scheduler.py              # AsyncIOSchedulerImpl（APScheduler 实现）
└── interfaces/
    ├── __init__.py
    ├── dependencies.py           # get_scheduler() 依赖注入
    └── module_registry.py        # ModuleRegistry 模块任务注册中心

业务模块（如 data_engineering）
└── interfaces/
    └── schedulers/
        ├── __init__.py           # create_scheduled_tasks() 入口
        └── tasks.py              # 任务配置 + async callable 工厂

app/modules/
└── __init__.py                   # register_scheduled_tasks()：所有业务模块注册定时任务

interfaces 层（组装）
└── main.py                       # lifespan 中初始化、注册、启动、关闭调度器
```

### 3.2 依赖方向

```
data_engineering.interfaces.schedulers → foundation.application（使用 ScheduledTaskConfig, CronTrigger）
data_engineering.interfaces.schedulers → data_engineering.application（使用 Command, Handler）
data_engineering.interfaces.schedulers → data_engineering.infrastructure（构造 Gateway, Repository）
foundation.infrastructure → foundation.application（实现 Scheduler Protocol）
app.modules.__init__ → foundation.interfaces（使用 ModuleRegistry）
app.modules.__init__ → 各业务模块 interfaces.schedulers（获取任务定义）
interfaces.main → foundation.infrastructure（创建 AsyncIOSchedulerImpl）
interfaces.main → foundation.interfaces（使用 ModuleRegistry）
```

**关键原则：**
- foundation **不主动 import** 任何业务模块
- 业务模块**主动注册**自己的任务到 `ModuleRegistry`
- foundation 只提供**抽象接口和注册机制**
- 定时任务在 interfaces 层构造 Handler（与 Router 中 `Depends()` 组装 Handler 同层）

---

## 4. 核心接口设计

### 4.1 foundation/application/scheduler.py

```python
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class CronTrigger:
    """Cron 触发器配置（纯数据值对象，不含 APScheduler 依赖）。

    Attributes:
        hour: 小时（0-23），None 表示每小时
        minute: 分钟（0-59），None 表示每分钟
        second: 秒（0-59），默认 0
        day_of_week: 星期几（0-6 或 'mon'-'sun'），None 表示每天
        day: 日期（1-31），None 表示每日
        month: 月份（1-12），None 表示每月
    """

    hour: int | None = None
    minute: int | None = None
    second: int = 0
    day_of_week: int | str | None = None
    day: int | None = None
    month: int | None = None

    def __post_init__(self) -> None:
        """校验字段范围，提前暴露配置错误。"""
        if self.hour is not None and not (0 <= self.hour <= 23):
            raise ValueError(f"hour 必须在 0-23 之间，实际: {self.hour}")
        if self.minute is not None and not (0 <= self.minute <= 59):
            raise ValueError(f"minute 必须在 0-59 之间，实际: {self.minute}")
        if not (0 <= self.second <= 59):
            raise ValueError(f"second 必须在 0-59 之间，实际: {self.second}")


@dataclass(frozen=True)
class ScheduledTaskConfig:
    """定时任务配置（纯数据，不含业务逻辑）。

    Attributes:
        id: 任务唯一标识，用于日志和错误追踪（如 'de.sync_stock_daily_increment'）
        trigger: 触发器配置（cron 表达式）
        name: 任务中文名称，用于日志展示
        module: 所属模块名（如 'data_engineering'）
        max_instances: 最大并发实例数，默认 1（防止任务重叠）
        coalesce: 是否合并错过的执行，默认 True
        misfire_grace_time: 错过执行的补执行时间窗口（秒），默认 7200（2 小时）
    """

    id: str
    trigger: CronTrigger
    name: str
    module: str
    max_instances: int = 1
    coalesce: bool = True
    misfire_grace_time: int = 7200


class Scheduler(Protocol):
    """调度器接口（由 infrastructure 实现）。"""

    def add_job(
        self,
        config: ScheduledTaskConfig,
        task_callable: Callable[[], Awaitable[None]],
    ) -> None:
        """添加定时任务。

        Args:
            config: 任务配置
            task_callable: 任务执行函数（无参 async 函数，调度器 await 此函数）
        """
        ...

    def start(self) -> None:
        """启动调度器。"""
        ...

    def shutdown(self, wait: bool = True) -> None:
        """关闭调度器。

        Args:
            wait: 是否等待正在执行的任务完成
        """
        ...
```

### 4.2 foundation/infrastructure/scheduler.py

```python
import time
from collections.abc import Awaitable, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger as APSCronTrigger

from app.foundation.application.scheduler import ScheduledTaskConfig
from app.shared_kernel.infrastructure.logging import get_logger

logger = get_logger(__name__)


class AsyncIOSchedulerImpl:
    """基于 APScheduler 的调度器实现。

    Attributes:
        _scheduler: APScheduler AsyncIOScheduler 实例
        _logger: 绑定了 component='scheduler' 的 structlog logger
    """

    def __init__(self) -> None:
        self._scheduler = AsyncIOScheduler()
        self._logger = logger.bind(component="scheduler")

    def add_job(
        self,
        config: ScheduledTaskConfig,
        task_callable: Callable[[], Awaitable[None]],
    ) -> None:
        """添加定时任务，自动包装日志和错误处理。

        错误处理策略：
        - 任务失败时记录详细日志（任务 ID、模块名、异常信息、耗时）
        - 不自动重试，避免脏数据
        - 通过日志系统告警，由人工判断是否补执行
        """

        async def wrapped_task() -> None:
            start = time.monotonic()
            self._logger.info(
                "任务开始执行",
                task_id=config.id,
                task_name=config.name,
                module=config.module,
            )
            try:
                await task_callable()
                duration_ms = int((time.monotonic() - start) * 1000)
                self._logger.info(
                    "任务执行成功",
                    task_id=config.id,
                    task_name=config.name,
                    module=config.module,
                    duration_ms=duration_ms,
                )
            except Exception:
                duration_ms = int((time.monotonic() - start) * 1000)
                self._logger.error(
                    "任务执行失败",
                    task_id=config.id,
                    task_name=config.name,
                    module=config.module,
                    duration_ms=duration_ms,
                    exc_info=True,
                )
                raise  # 重新抛出，让 APScheduler 记录为失败

        # 将 CronTrigger 值对象转换为 APScheduler CronTrigger
        trigger_kwargs: dict = {}
        if config.trigger.hour is not None:
            trigger_kwargs["hour"] = config.trigger.hour
        if config.trigger.minute is not None:
            trigger_kwargs["minute"] = config.trigger.minute
        if config.trigger.second != 0:
            trigger_kwargs["second"] = config.trigger.second
        if config.trigger.day_of_week is not None:
            trigger_kwargs["day_of_week"] = config.trigger.day_of_week
        if config.trigger.day is not None:
            trigger_kwargs["day"] = config.trigger.day
        if config.trigger.month is not None:
            trigger_kwargs["month"] = config.trigger.month

        aps_trigger = APSCronTrigger(**trigger_kwargs)

        self._scheduler.add_job(
            wrapped_task,
            trigger=aps_trigger,
            id=config.id,
            name=config.name,
            max_instances=config.max_instances,
            coalesce=config.coalesce,
            misfire_grace_time=config.misfire_grace_time,
        )

        self._logger.info(
            "任务已注册",
            task_id=config.id,
            task_name=config.name,
            module=config.module,
            trigger=str(aps_trigger),
        )

    def start(self) -> None:
        """启动调度器。"""
        self._scheduler.start()
        self._logger.info("调度器已启动")

    def shutdown(self, wait: bool = True) -> None:
        """关闭调度器。"""
        self._scheduler.shutdown(wait=wait)
        self._logger.info("调度器已关闭", wait=wait)
```

### 4.3 foundation/interfaces/dependencies.py

```python
from fastapi import Request

from app.foundation.application.scheduler import Scheduler


def get_scheduler(request: Request) -> Scheduler:
    """获取调度器实例（从 app.state 注入）。

    返回 Scheduler Protocol 类型，不暴露具体实现。
    """
    return request.app.state.scheduler
```

### 4.4 foundation/interfaces/module_registry.py

```python
from collections.abc import Awaitable, Callable
from typing import TypeAlias

from app.foundation.application.scheduler import Scheduler, ScheduledTaskConfig

# 任务工厂签名：返回 (配置列表, {任务ID: async callable}) 元组
ScheduledTaskFactory: TypeAlias = Callable[
    [],
    tuple[list[ScheduledTaskConfig], dict[str, Callable[[], Awaitable[None]]]],
]


class ModuleRegistry:
    """模块任务注册中心。

    管理所有业务模块注册的定时任务工厂。foundation 不主动 import 任何业务模块，
    由业务模块主动调用 register_scheduled_tasks() 注册。

    使用实例而非类变量，避免测试之间状态泄漏。
    """

    def __init__(self) -> None:
        self._scheduled_task_factories: list[ScheduledTaskFactory] = []

    def register_scheduled_tasks(self, factory: ScheduledTaskFactory) -> None:
        """注册一个模块的任务工厂。

        Args:
            factory: 无参函数，返回 (configs, task_callables) 元组
                configs: 任务配置列表
                task_callables: 任务 ID -> async callable 的映射
        """
        self._scheduled_task_factories.append(factory)

    def register_all_to_scheduler(self, scheduler: Scheduler) -> None:
        """遍历所有已注册的任务工厂，将任务添加到调度器。

        Args:
            scheduler: 调度器实例

        Raises:
            ValueError: 若某个 config.id 在 task_callables 中找不到对应的工厂函数
        """
        for factory in self._scheduled_task_factories:
            configs, task_callables = factory()
            for config in configs:
                if config.id not in task_callables:
                    raise ValueError(
                        f"任务 '{config.id}'（模块 '{config.module}'）未找到对应的 async callable"
                    )
                scheduler.add_job(config, task_callables[config.id])
```

---

## 5. 业务模块任务定义

### 5.1 data_engineering/interfaces/schedulers/tasks.py

**关键设计**：任务执行函数自行管理 Session 生命周期——创建 session → 构造 Handler → 执行 → 关闭 session。不通过 Mediator 分发，因为 Mediator 当前未注册 handler factory，且定时任务无 HTTP Request 上下文。

```python
from collections.abc import Awaitable, Callable
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import settings
from app.foundation.application.scheduler import CronTrigger, ScheduledTaskConfig
from app.modules.data_engineering.application.commands.sync_stock_daily_increment import (
    SyncStockDailyIncrement,
)
from app.modules.data_engineering.application.commands.sync_stock_daily_increment_handler import (
    SyncStockDailyIncrementHandler,
)
from app.modules.data_engineering.domain.value_objects.data_source import DataSource
from app.modules.data_engineering.infrastructure import (
    SqlAlchemyStockBasicRepository,
    SqlAlchemyStockDailyRepository,
    TuShareStockDailyGateway,
)
from app.shared_kernel.infrastructure.logging import get_logger
from app.shared_kernel.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork

logger = get_logger(__name__)


def get_scheduled_tasks() -> list[ScheduledTaskConfig]:
    """返回 data_engineering 模块的所有定时任务配置。"""
    return [
        ScheduledTaskConfig(
            id="de.sync_stock_daily_increment",
            trigger=CronTrigger(hour=16, minute=30),  # 每天 16:30（收盘后 30 分钟）
            name="同步股票日线数据（增量）",
            module="data_engineering",
            max_instances=1,
            coalesce=True,
            misfire_grace_time=7200,  # 2 小时补执行窗口
        ),
        # 可添加更多任务...
    ]


def create_task_callables(
    session_factory: async_sessionmaker[AsyncSession],
) -> dict[str, Callable[[], Awaitable[None]]]:
    """创建任务 ID -> async callable 的映射。

    每个 async callable 自行管理 session 生命周期：
    创建 session → 构造 Handler 及其依赖 → 执行 command → 关闭 session

    Args:
        session_factory: SQLAlchemy 异步 session 工厂（从 Database.session_factory 获取）
    """

    async def sync_stock_daily_increment() -> None:
        """增量同步股票日线数据。"""
        session: AsyncSession = session_factory()
        try:
            gateway = TuShareStockDailyGateway(token=settings.TUSHARE_TOKEN)
            daily_repo = SqlAlchemyStockDailyRepository(session)
            basic_repo = SqlAlchemyStockBasicRepository(session)
            uow = SqlAlchemyUnitOfWork(session)

            handler = SyncStockDailyIncrementHandler(
                gateway=gateway,
                daily_repo=daily_repo,
                basic_repo=basic_repo,
                uow=uow,
            )
            command = SyncStockDailyIncrement(
                trade_date=date.today() - timedelta(days=1),
            )
            await handler.handle(command)
        finally:
            await session.close()

    return {
        "de.sync_stock_daily_increment": sync_stock_daily_increment,
    }
```

### 5.2 data_engineering/interfaces/schedulers/__init__.py

```python
"""data_engineering 模块定时任务注册入口。"""

from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.foundation.application.scheduler import ScheduledTaskConfig

from .tasks import create_task_callables, get_scheduled_tasks


def create_scheduled_tasks(
    session_factory: async_sessionmaker[AsyncSession],
) -> tuple[list[ScheduledTaskConfig], dict[str, Callable[[], Awaitable[None]]]]:
    """返回本模块的任务配置和 async callable 映射（供 ModuleRegistry 使用）。

    Args:
        session_factory: SQLAlchemy 异步 session 工厂
    """
    configs = get_scheduled_tasks()
    callables = create_task_callables(session_factory)
    return configs, callables
```

---

## 6. 模块注册

### 6.1 app/modules/__init__.py

```python
"""模块定时任务注册中心。

所有业务模块在此注册自己的定时任务。Router 注册仍由
app/interfaces/module_registry.py 的 register_modules() 负责，职责分离。
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.foundation.interfaces.module_registry import ModuleRegistry


def register_scheduled_tasks(
    registry: ModuleRegistry,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """注册所有业务模块的定时任务到 ModuleRegistry。

    Args:
        registry: 模块注册中心实例
        session_factory: SQLAlchemy 异步 session 工厂
    """
    # --- data_engineering 模块 ---
    from app.modules.data_engineering.interfaces.schedulers import create_scheduled_tasks

    registry.register_scheduled_tasks(
        lambda: create_scheduled_tasks(session_factory)
    )

    # --- 新增模块时在此追加 ---
```

### 6.2 interfaces/main.py（扩展部分）

仅展示相对于现有 main.py 的**增量变更**，不重复已有代码：

```python
# === 新增 import ===
from app.foundation.infrastructure.scheduler import AsyncIOSchedulerImpl
from app.foundation.interfaces.module_registry import ModuleRegistry
from app.modules import register_scheduled_tasks


# === lifespan 中的增量逻辑（在 mediator 之后、yield 之前） ===

    # 初始化调度器
    scheduler = AsyncIOSchedulerImpl()
    app.state.scheduler = scheduler

    # 注册所有业务模块的定时任务
    registry = ModuleRegistry()
    register_scheduled_tasks(registry, db.session_factory)
    registry.register_all_to_scheduler(scheduler)

    # 启动调度器
    scheduler.start()
    logger.info("调度器已启动，任务注册完成")

    yield

    # === yield 之后、db.dispose() 之前 ===
    scheduler.shutdown(wait=True)
```

**完整 lifespan 示例**（供实现参考）：

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging(log_level=settings.LOG_LEVEL, app_env=settings.APP_ENV)
    logger.info("Application starting up", app_name=settings.APP_NAME, env=settings.APP_ENV)

    db = Database(url=settings.DATABASE_URL, echo=False)
    app.state.db = db

    mediator = Mediator()
    _register_handlers(mediator, db)
    app.state.mediator = mediator

    # 初始化调度器
    scheduler = AsyncIOSchedulerImpl()
    app.state.scheduler = scheduler

    # 注册所有业务模块的定时任务
    registry = ModuleRegistry()
    register_scheduled_tasks(registry, db.session_factory)
    registry.register_all_to_scheduler(scheduler)

    # 启动调度器
    scheduler.start()

    yield

    # 关闭调度器（等待正在执行的任务完成）
    scheduler.shutdown(wait=True)
    await db.dispose()
    logger.info("Application shut down")
```

---

## 7. 错误处理策略

### 7.1 日志记录

任务执行失败时的日志输出示例：

```json
{
    "level": "error",
    "timestamp": "2026-02-24T16:30:05.123Z",
    "component": "scheduler",
    "task_id": "de.sync_stock_daily_increment",
    "task_name": "同步股票日线数据（增量）",
    "module": "data_engineering",
    "message": "任务执行失败",
    "duration_ms": 3215,
    "exception": "TushareGatewayError: 接口调用失败",
    "traceback": "..."
}
```

### 7.2 不自动重试的理由

1. **数据一致性**：数据同步任务失败可能是数据质量问题，重试可能导致脏数据
2. **人工确认**：需要人工判断是否需要补执行，避免自动化带来的风险
3. **简单有效**：通过详细日志，运维人员可以快速定位问题并手动触发

---

## 8. 扩展性考虑

### 8.1 未来持久化支持

当前使用内存 Job Store，未来如需持久化，只需修改 `foundation/infrastructure/scheduler.py`：

```python
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

class AsyncIOSchedulerImpl:
    def __init__(self, db_url: str | None = None) -> None:
        jobstores = {}
        if db_url:
            jobstores['default'] = SQLAlchemyJobStore(url=db_url)
        self._scheduler = AsyncIOScheduler(jobstores=jobstores)
```

### 8.2 未来分布式支持

当前为单机调度，未来如需分布式，可通过：

1. **单实例调度器 + HTTP 调用**：只有一个实例运行调度器，通过 HTTP 调用其他服务
2. **迁移到 Celery Beat**：保留 Scheduler Protocol 接口，切换实现

### 8.3 未来迁移到 Mediator 分发

当前任务直接构造 Handler 执行。未来若 Mediator 支持 scope-aware handler factory（自动管理 session 生命周期），可将任务执行改为 `mediator.send(command)`，任务函数只需构造 command 即可。

---

## 9. 测试策略

### 9.1 单元测试

通过依赖注入 mock，验证任务注册和执行逻辑：

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.foundation.application.scheduler import CronTrigger, ScheduledTaskConfig


class TestAsyncIOSchedulerImpl:
    """AsyncIOSchedulerImpl 单元测试。"""

    def test_add_job_registers_to_apscheduler(self):
        """验证 add_job 正确转换配置并注册到 APScheduler。"""
        from app.foundation.infrastructure.scheduler import AsyncIOSchedulerImpl

        scheduler = AsyncIOSchedulerImpl()
        scheduler._scheduler = MagicMock()  # mock 内部 APScheduler

        config = ScheduledTaskConfig(
            id="test_task",
            trigger=CronTrigger(hour=16, minute=30),
            name="测试任务",
            module="test",
        )
        task = AsyncMock()
        scheduler.add_job(config, task)

        scheduler._scheduler.add_job.assert_called_once()
        call_kwargs = scheduler._scheduler.add_job.call_args
        assert call_kwargs.kwargs["id"] == "test_task"
        assert call_kwargs.kwargs["max_instances"] == 1
        assert call_kwargs.kwargs["misfire_grace_time"] == 7200

    @pytest.mark.asyncio
    async def test_wrapped_task_logs_success(self):
        """验证 wrapped_task 在成功时记录日志。"""
        from app.foundation.infrastructure.scheduler import AsyncIOSchedulerImpl

        scheduler = AsyncIOSchedulerImpl()
        scheduler._scheduler = MagicMock()

        executed = False

        async def task():
            nonlocal executed
            executed = True

        config = ScheduledTaskConfig(
            id="test_task",
            trigger=CronTrigger(hour=16, minute=30),
            name="测试任务",
            module="test",
        )
        scheduler.add_job(config, task)

        # 获取 wrapped_task 并直接调用
        wrapped = scheduler._scheduler.add_job.call_args.args[0]
        await wrapped()
        assert executed

    @pytest.mark.asyncio
    async def test_wrapped_task_logs_and_reraises_on_failure(self):
        """验证 wrapped_task 在失败时记录日志并重新抛出异常。"""
        from app.foundation.infrastructure.scheduler import AsyncIOSchedulerImpl

        scheduler = AsyncIOSchedulerImpl()
        scheduler._scheduler = MagicMock()

        async def failing_task():
            raise RuntimeError("模拟失败")

        config = ScheduledTaskConfig(
            id="test_task",
            trigger=CronTrigger(hour=16, minute=30),
            name="测试任务",
            module="test",
        )
        scheduler.add_job(config, failing_task)

        wrapped = scheduler._scheduler.add_job.call_args.args[0]
        with pytest.raises(RuntimeError, match="模拟失败"):
            await wrapped()


class TestCronTrigger:
    """CronTrigger 值对象验证测试。"""

    def test_valid_trigger(self):
        trigger = CronTrigger(hour=16, minute=30)
        assert trigger.hour == 16
        assert trigger.minute == 30

    def test_invalid_hour_raises(self):
        with pytest.raises(ValueError, match="hour"):
            CronTrigger(hour=25)

    def test_invalid_minute_raises(self):
        with pytest.raises(ValueError, match="minute"):
            CronTrigger(minute=60)


class TestModuleRegistry:
    """ModuleRegistry 单元测试。"""

    def test_register_and_apply(self):
        from app.foundation.interfaces.module_registry import ModuleRegistry

        registry = ModuleRegistry()
        mock_scheduler = MagicMock()

        config = ScheduledTaskConfig(
            id="test_task",
            trigger=CronTrigger(hour=8),
            name="测试",
            module="test",
        )
        task = AsyncMock()

        registry.register_scheduled_tasks(lambda: ([config], {"test_task": task}))
        registry.register_all_to_scheduler(mock_scheduler)

        mock_scheduler.add_job.assert_called_once_with(config, task)

    def test_missing_callable_raises(self):
        from app.foundation.interfaces.module_registry import ModuleRegistry

        registry = ModuleRegistry()
        mock_scheduler = MagicMock()

        config = ScheduledTaskConfig(
            id="missing_task",
            trigger=CronTrigger(hour=8),
            name="测试",
            module="test",
        )

        registry.register_scheduled_tasks(lambda: ([config], {}))
        with pytest.raises(ValueError, match="missing_task"):
            registry.register_all_to_scheduler(mock_scheduler)

    def test_instances_are_isolated(self):
        """验证不同 ModuleRegistry 实例之间状态隔离。"""
        from app.foundation.interfaces.module_registry import ModuleRegistry

        r1 = ModuleRegistry()
        r2 = ModuleRegistry()

        r1.register_scheduled_tasks(lambda: ([], {}))
        assert len(r1._scheduled_task_factories) == 1
        assert len(r2._scheduled_task_factories) == 0
```

### 9.2 集成测试

验证定时任务可以正确构造 Handler 并执行（使用测试数据库）：

```python
@pytest.mark.asyncio
async def test_sync_stock_daily_increment_task_integration(test_db):
    """验证定时任务函数能正确构造 Handler 并执行。"""
    from app.modules.data_engineering.interfaces.schedulers.tasks import (
        create_task_callables,
    )

    callables = create_task_callables(test_db.session_factory)
    task = callables["de.sync_stock_daily_increment"]

    # 在测试环境中执行任务（需要 mock gateway）
    # ...
```

### 9.3 架构测试

```python
def test_foundation_does_not_import_business_modules():
    """由 import-linter forbidden contract 自动检查。"""
    pass


def test_scheduler_tasks_directory_exists_for_modules_with_tasks():
    """检查注册了定时任务的模块都有 interfaces/schedulers/ 目录。"""
    pass
```

---

## 10. 依赖要求

需要在 `pyproject.toml` 中添加：

```toml
dependencies = [
    # ... 现有依赖 ...
    "APScheduler>=3.10.0",
]
```

---

## 11. 文件清单

**新增文件：**

- `src/app/foundation/__init__.py`
- `src/app/foundation/application/__init__.py`
- `src/app/foundation/application/scheduler.py` — Scheduler Protocol + ScheduledTaskConfig + CronTrigger
- `src/app/foundation/infrastructure/__init__.py`
- `src/app/foundation/infrastructure/scheduler.py` — AsyncIOSchedulerImpl
- `src/app/foundation/interfaces/__init__.py`
- `src/app/foundation/interfaces/dependencies.py` — get_scheduler()
- `src/app/foundation/interfaces/module_registry.py` — ModuleRegistry
- `src/app/modules/data_engineering/interfaces/schedulers/tasks.py` — 任务配置 + async callable

**修改文件：**

- `src/app/modules/__init__.py` — 新增 register_scheduled_tasks()
- `src/app/modules/data_engineering/interfaces/schedulers/__init__.py` — 新增 create_scheduled_tasks()
- `src/app/interfaces/main.py` — lifespan 中增加调度器初始化
- `pyproject.toml` — 添加 APScheduler 依赖 + import-linter 配置

---

## 12. 架构守护

### 12.1 依赖方向检查

import-linter 配置变更（`pyproject.toml`）：

```toml
# 现有 containers 新增 app.foundation
[tool.importlinter]
root_package = "app"

[[tool.importlinter.contracts]]
name = "DDD layer boundaries"
type = "layers"
layers = [
    "(interfaces)",
    "application | infrastructure",
    "domain",
]
containers = [
    "app.shared_kernel",
    "app.modules.data_engineering",
    "app.foundation",
]

# 新增：foundation 不依赖业务模块
[[tool.importlinter.contracts]]
name = "foundation does not depend on business modules"
type = "forbidden"
source_modules = [
    "app.foundation",
]
forbidden_modules = [
    "app.modules.data_engineering",
    "app.modules.knowledge_center",
    # 新增业务模块时在此追加
]
```

### 12.2 模块注册检查

测试用例（`tests/architecture/test_module_registration.py`）：

```python
def test_all_modules_register_scheduled_tasks():
    """确保所有模块都在 modules/__init__.py 中注册。"""
    from app.foundation.interfaces.module_registry import ModuleRegistry
    from unittest.mock import MagicMock

    registry = ModuleRegistry()
    mock_session_factory = MagicMock()

    from app.modules import register_scheduled_tasks
    register_scheduled_tasks(registry, mock_session_factory)

    # 验证至少注册了 data_engineering 模块的任务
    assert len(registry._scheduled_task_factories) >= 1
```

---

## 13. 使用指南：新增定时任务

### 步骤 1：定义 Command 和 Handler（已有模式）

在业务模块的 `application/commands/` 中按现有模式创建。

### 步骤 2：创建任务配置和 async callable

```python
# my_module/interfaces/schedulers/tasks.py
from app.foundation.application.scheduler import CronTrigger, ScheduledTaskConfig

def get_scheduled_tasks() -> list[ScheduledTaskConfig]:
    return [
        ScheduledTaskConfig(
            id='mm.daily_task',
            trigger=CronTrigger(hour=8, minute=0),
            name='我的模块每日任务',
            module='my_module',
        ),
    ]

def create_task_callables(session_factory):
    async def daily_task():
        session = session_factory()
        try:
            # 构造 Handler 及其依赖
            handler = MyModuleDailyHandler(...)
            await handler.handle(MyModuleDailyCommand())
        finally:
            await session.close()

    return {'mm.daily_task': daily_task}
```

### 步骤 3：创建模块入口

```python
# my_module/interfaces/schedulers/__init__.py
from .tasks import get_scheduled_tasks, create_task_callables

def create_scheduled_tasks(session_factory):
    return get_scheduled_tasks(), create_task_callables(session_factory)
```

### 步骤 4：在 `app/modules/__init__.py` 中注册

```python
from app.modules.my_module.interfaces.schedulers import create_scheduled_tasks as mm_tasks

registry.register_scheduled_tasks(lambda: mm_tasks(session_factory))
```

### 步骤 5：更新 import-linter forbidden contract（如果是新模块）

在 `pyproject.toml` 的 `forbidden_modules` 中追加新模块路径。

---

## 14. 关键设计决策说明

### 14.1 为什么任务直接构造 Handler 而不走 Mediator？

- 当前 `_register_handlers()` 为空，Handler 通过 Router 的 `Depends()` 注入
- Mediator 未注册 handler factory，`mediator.send(command)` 会 KeyError
- 定时任务无 HTTP Request 上下文，无法使用 `Depends(get_uow)` 获取 session
- 直接构造 Handler 是最简单、最可靠的方案；与 Router 中 `dependencies.py` 组装 Handler 的模式一致（都在 interfaces 层完成组装）

### 14.2 为什么 ModuleRegistry 使用实例而非类变量？

- 类变量 `list = []` 被所有实例共享，测试之间状态泄漏
- 多次调用会重复注册任务
- 实例化后状态隔离，测试安全

### 14.3 为什么 CronTrigger 改为 frozen dataclass？

- 项目约定值对象使用 `@dataclass(frozen=True)`
- 不可变性保证配置不被意外修改
- `__post_init__` 提前校验参数范围，避免运行时才由 APScheduler 报错

---

## 15. 待办事项

- [ ] 添加 APScheduler 依赖到 `pyproject.toml`
- [ ] 更新 `pyproject.toml` 的 import-linter 配置
- [ ] 创建 `src/app/foundation/` 目录结构（含所有 `__init__.py`）
- [ ] 实现 foundation 调度器核心接口（application + infrastructure）
- [ ] 实现 ModuleRegistry 注册机制（interfaces）
- [ ] 实现 data_engineering 的定时任务（interfaces/schedulers/tasks.py）
- [ ] 扩展 `app/modules/__init__.py`
- [ ] 扩展 `interfaces/main.py` 的 lifespan
- [ ] 编写单元测试、集成测试和架构测试
- [ ] 运行 `make ci` 验证
- [ ] 更新开发文档（添加定时任务使用指南）
