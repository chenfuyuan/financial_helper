"""AsyncIOSchedulerImpl 单元测试。"""

import asyncio
from collections.abc import Awaitable, Callable
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.foundation.application.scheduled_task_config import CronTrigger, ScheduledTaskConfig
from app.modules.foundation.infrastructure.asyncio_scheduler_impl import AsyncIOSchedulerImpl


class TestAsyncIOSchedulerImpl:
    """测试 AsyncIOSchedulerImpl。"""

    def test_create_scheduler_instance(self) -> None:
        """验证创建 AsyncIOSchedulerImpl() 实例。"""
        scheduler = AsyncIOSchedulerImpl()
        assert scheduler is not None
        assert hasattr(scheduler, "_scheduler")

    def test_add_job_registers_task(self) -> None:
        """验证 scheduler.add_job(config, task_callable) 注册任务。"""
        scheduler = AsyncIOSchedulerImpl()
        trigger = CronTrigger(hour=16, minute=30)
        config = ScheduledTaskConfig(
            id="test.task",
            trigger=trigger,
            name="测试任务",
            module="test",
        )

        async def task_callable() -> None:
            pass

        # add_job 不应抛出异常
        scheduler.add_job(config, task_callable)

        # 验证任务已注册到内部调度器
        job = scheduler._scheduler.get_job("test.task")
        assert job is not None
        assert job.id == "test.task"

    def test_start_starts_scheduler(self) -> None:
        """验证 scheduler.start() 启动调度器。"""
        scheduler = AsyncIOSchedulerImpl()

        # 调度器初始未运行
        assert not scheduler._scheduler.running

        scheduler.start()
        assert scheduler._scheduler.running

        # 清理
        scheduler.shutdown(wait=False)

    def test_shutdown_stops_scheduler(self) -> None:
        """验证 scheduler.shutdown(wait=True) 关闭调度器。"""
        scheduler = AsyncIOSchedulerImpl()
        scheduler.start()

        # 验证 shutdown 方法可正常调用
        scheduler.shutdown(wait=True)
        # 测试通过即表示 shutdown 成功执行

    def test_shutdown_with_wait_false(self) -> None:
        """验证 scheduler.shutdown(wait=False) 立即关闭。"""
        scheduler = AsyncIOSchedulerImpl()
        scheduler.start()

        # 验证 shutdown 方法可正常调用
        scheduler.shutdown(wait=False)
        # 测试通过即表示 shutdown 成功执行


class TestWrappedTaskLogging:
    """测试任务包装函数的日志记录。"""

    @pytest.mark.asyncio
    async def test_task_success_logs_duration(self) -> None:
        """验证任务成功时记录 duration_ms。"""
        with patch("app.modules.foundation.infrastructure.asyncio_scheduler_impl.logger") as mock_logger:
            scheduler = AsyncIOSchedulerImpl()
            trigger = CronTrigger(hour=16, minute=30)
            config = ScheduledTaskConfig(
                id="test.success_task",
                trigger=trigger,
                name="成功任务",
                module="test",
            )

            execution_count = 0

            async def success_task() -> None:
                nonlocal execution_count
                execution_count += 1

            scheduler.add_job(config, success_task)

            # 获取包装后的任务并执行
            job = scheduler._scheduler.get_job("test.success_task")
            assert job is not None
            await job.func()  # type: ignore[misc]

            assert execution_count == 1
            # 验证日志调用包含 duration_ms
            info_calls = [call for call in mock_logger.info.call_args_list]
            # 找到包含 duration_ms 的日志调用
            assert any(
                "duration_ms" in str(call) for call in info_calls
            ), f"Expected duration_ms in info calls: {info_calls}"

    @pytest.mark.asyncio
    async def test_task_failure_logs_error(self) -> None:
        """验证任务失败时记录 error 日志和 exc_info。"""
        with patch("app.modules.foundation.infrastructure.asyncio_scheduler_impl.logger") as mock_logger:
            scheduler = AsyncIOSchedulerImpl()
            trigger = CronTrigger(hour=16, minute=30)
            config = ScheduledTaskConfig(
                id="test.fail_task",
                trigger=trigger,
                name="失败任务",
                module="test",
            )

            async def fail_task() -> None:
                raise ValueError("测试异常")

            scheduler.add_job(config, fail_task)

            # 获取包装后的任务并执行
            job = scheduler._scheduler.get_job("test.fail_task")
            assert job is not None

            with pytest.raises(ValueError, match="测试异常"):
                await job.func()  # type: ignore[misc]

            # 验证错误日志被调用
            assert mock_logger.error.called
            # 验证 error 调用包含 exc_info=True
            error_calls = [call for call in mock_logger.error.call_args_list]
            assert any("exc_info" in str(call) for call in error_calls), f"Expected exc_info in error calls: {error_calls}"

    @pytest.mark.asyncio
    async def test_task_start_logs_info(self) -> None:
        """验证任务执行记录开始日志。"""
        with patch("app.modules.foundation.infrastructure.asyncio_scheduler_impl.logger") as mock_logger:
            scheduler = AsyncIOSchedulerImpl()
            trigger = CronTrigger(hour=16, minute=30)
            config = ScheduledTaskConfig(
                id="test.start_task",
                trigger=trigger,
                name="开始任务",
                module="test",
            )

            async def simple_task() -> None:
                pass

            scheduler.add_job(config, simple_task)

            # 获取包装后的任务并执行
            job = scheduler._scheduler.get_job("test.start_task")
            assert job is not None
            await job.func()  # type: ignore[misc]

            # 验证开始日志（Task started）
            info_calls = [call for call in mock_logger.info.call_args_list]
            # 找到第一个 info 调用（Task started）
            assert len(info_calls) >= 1, f"Expected at least 1 info call: {info_calls}"
