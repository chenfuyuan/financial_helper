"""ModuleRegistry 单元测试。"""

from collections.abc import Awaitable, Callable
from typing import TypeAlias
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.foundation.application.scheduled_task_config import CronTrigger, ScheduledTaskConfig

# 定义任务工厂类型
ScheduledTaskFactory: TypeAlias = Callable[
    [],
    tuple[list[ScheduledTaskConfig], dict[str, Callable[[], Awaitable[None]]]],
]


class TestModuleRegistry:
    """测试 ModuleRegistry。"""

    def test_create_module_registry_instance(self) -> None:
        """验证创建 ModuleRegistry 实例。"""
        from app.modules.foundation.application.module_registry import ModuleRegistry

        registry = ModuleRegistry()
        assert registry is not None

    def test_instance_state_isolation(self) -> None:
        """验证实例状态隔离（r1 和 r2 的 _scheduled_task_factories 独立）。"""
        from app.modules.foundation.application.module_registry import ModuleRegistry

        r1 = ModuleRegistry()
        r2 = ModuleRegistry()

        # 向 r1 注册一个工厂
        def factory1() -> tuple[list[ScheduledTaskConfig], dict[str, Callable[[], Awaitable[None]]]]:
            return [], {}

        r1.register_scheduled_tasks(factory1)

        # r2 的工厂列表应为空
        assert len(r2._scheduled_task_factories) == 0
        assert len(r1._scheduled_task_factories) == 1

    def test_register_scheduled_tasks_adds_factory(self) -> None:
        """验证 register_scheduled_tasks(factory) 添加任务工厂。"""
        from app.modules.foundation.application.module_registry import ModuleRegistry

        registry = ModuleRegistry()

        def factory() -> tuple[list[ScheduledTaskConfig], dict[str, Callable[[], Awaitable[None]]]]:
            return [], {}

        registry.register_scheduled_tasks(factory)

        assert len(registry._scheduled_task_factories) == 1
        assert registry._scheduled_task_factories[0] is factory

    def test_register_all_to_scheduler_calls_all_factories(self) -> None:
        """验证 register_all_to_scheduler(scheduler) 调用所有工厂。"""
        from app.modules.foundation.application.module_registry import ModuleRegistry

        registry = ModuleRegistry()

        # 创建模拟任务配置和 callable
        trigger = CronTrigger(hour=16, minute=30)
        config = ScheduledTaskConfig(
            id="test.task1",
            trigger=trigger,
            name="测试任务1",
            module="test",
        )

        async def task_callable1() -> None:
            pass

        factory_called = False

        def factory() -> tuple[list[ScheduledTaskConfig], dict[str, Callable[[], Awaitable[None]]]]:
            nonlocal factory_called
            factory_called = True
            return [config], {"test.task1": task_callable1}

        registry.register_scheduled_tasks(factory)

        # 创建模拟调度器
        mock_scheduler = MagicMock()
        mock_scheduler.add_job = MagicMock()

        registry.register_all_to_scheduler(mock_scheduler)

        assert factory_called
        mock_scheduler.add_job.assert_called_once()
        # 验证调用参数
        call_args = mock_scheduler.add_job.call_args
        assert call_args[0][0] == config  # config 参数


class TestModuleRegistryValidation:
    """测试 ModuleRegistry 任务验证。"""

    def test_config_id_missing_in_callables_raises_value_error(self) -> None:
        """验证 config.id 缺失时抛出 ValueError。"""
        from app.modules.foundation.application.module_registry import ModuleRegistry

        registry = ModuleRegistry()

        trigger = CronTrigger(hour=16, minute=30)
        config = ScheduledTaskConfig(
            id="test.missing_task",
            trigger=trigger,
            name="缺失 callable 的任务",
            module="test",
        )

        # 工厂返回的 callable 字典中没有对应的任务 ID
        def factory() -> tuple[list[ScheduledTaskConfig], dict[str, Callable[[], Awaitable[None]]]]:
            return [config], {}  # 空的 callable 字典

        registry.register_scheduled_tasks(factory)

        mock_scheduler = MagicMock()

        with pytest.raises(ValueError, match="test.missing_task.*test"):
            registry.register_all_to_scheduler(mock_scheduler)

    def test_validation_error_includes_task_id_and_module(self) -> None:
        """验证错误信息包含任务 ID 和模块名。"""
        from app.modules.foundation.application.module_registry import ModuleRegistry

        registry = ModuleRegistry()

        trigger = CronTrigger(hour=16, minute=30)
        config = ScheduledTaskConfig(
            id="de.sync_stock",
            trigger=trigger,
            name="股票同步",
            module="data_engineering",
        )

        def factory() -> tuple[list[ScheduledTaskConfig], dict[str, Callable[[], Awaitable[None]]]]:
            return [config], {}

        registry.register_scheduled_tasks(factory)

        mock_scheduler = MagicMock()

        with pytest.raises(ValueError, match="de.sync_stock") as exc_info:
            registry.register_all_to_scheduler(mock_scheduler)

        assert "data_engineering" in str(exc_info.value)
