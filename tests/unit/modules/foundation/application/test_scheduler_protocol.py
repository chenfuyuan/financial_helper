"""Scheduler Protocol 单元测试。"""

from collections.abc import Awaitable, Callable
from typing import Protocol, runtime_checkable

import pytest


class TestSchedulerProtocol:
    """测试 Scheduler Protocol。"""

    def test_can_import_scheduler_protocol(self) -> None:
        """验证可以导入 Scheduler Protocol。"""
        from app.modules.foundation.application.scheduler import Scheduler

        assert Scheduler is not None

    def test_scheduler_is_protocol(self) -> None:
        """验证 Scheduler 是 Protocol。"""
        from app.modules.foundation.application.scheduler import Scheduler

        # Protocol 类应该是 runtime_checkable 或继承自 Protocol
        assert issubclass(Scheduler, Protocol)

    def test_scheduler_has_add_job_method(self) -> None:
        """验证 Scheduler 包含 add_job 方法。"""
        from app.modules.foundation.application.scheduler import Scheduler

        # 检查 Protocol 有 add_job 方法签名
        assert hasattr(Scheduler, "add_job")

    def test_scheduler_has_start_method(self) -> None:
        """验证 Scheduler 包含 start 方法。"""
        from app.modules.foundation.application.scheduler import Scheduler

        assert hasattr(Scheduler, "start")

    def test_scheduler_has_shutdown_method(self) -> None:
        """验证 Scheduler 包含 shutdown 方法。"""
        from app.modules.foundation.application.scheduler import Scheduler

        assert hasattr(Scheduler, "shutdown")


class TestGetScheduler:
    """测试 get_scheduler 函数。"""

    def test_get_scheduler_returns_scheduler_type(self) -> None:
        """验证 get_scheduler() 返回 Scheduler 类型。"""
        from app.modules.foundation.application.scheduler import Scheduler
        from app.modules.foundation.interfaces.scheduler import get_scheduler

        scheduler = get_scheduler()
        assert isinstance(scheduler, Scheduler)
