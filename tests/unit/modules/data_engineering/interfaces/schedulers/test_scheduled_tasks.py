"""Data Engineering 模块定时任务测试。"""

import pytest

from app.modules.foundation.application.scheduled_task_config import CronTrigger


class TestGetScheduledTasks:
    """测试 get_scheduled_tasks 函数。"""

    def test_returns_task_config_list(self) -> None:
        """验证 get_scheduled_tasks() 返回任务配置列表。"""
        from app.modules.data_engineering.interfaces.schedulers.tasks import get_scheduled_tasks

        configs = get_scheduled_tasks()
        assert isinstance(configs, list)
        assert len(configs) >= 1

    def test_task_id_is_de_sync_stock_daily_increment(self) -> None:
        """验证任务 ID 为 de.sync_stock_daily_increment。"""
        from app.modules.data_engineering.interfaces.schedulers.tasks import get_scheduled_tasks

        configs = get_scheduled_tasks()
        task_ids = [config.id for config in configs]
        assert "de.sync_stock_daily_increment" in task_ids

    def test_trigger_is_cron_16_30(self) -> None:
        """验证 CronTrigger 配置为 hour=16, minute=30。"""
        from app.modules.data_engineering.interfaces.schedulers.tasks import get_scheduled_tasks

        configs = get_scheduled_tasks()
        sync_task = next((c for c in configs if c.id == "de.sync_stock_daily_increment"), None)
        assert sync_task is not None
        assert sync_task.trigger.hour == 16
        assert sync_task.trigger.minute == 30

    def test_max_instances_is_1(self) -> None:
        """验证 max_instances=1。"""
        from app.modules.data_engineering.interfaces.schedulers.tasks import get_scheduled_tasks

        configs = get_scheduled_tasks()
        sync_task = next((c for c in configs if c.id == "de.sync_stock_daily_increment"), None)
        assert sync_task is not None
        assert sync_task.max_instances == 1

    def test_coalesce_is_true(self) -> None:
        """验证 coalesce=True。"""
        from app.modules.data_engineering.interfaces.schedulers.tasks import get_scheduled_tasks

        configs = get_scheduled_tasks()
        sync_task = next((c for c in configs if c.id == "de.sync_stock_daily_increment"), None)
        assert sync_task is not None
        assert sync_task.coalesce is True

    def test_misfire_grace_time_is_7200(self) -> None:
        """验证 misfire_grace_time=7200。"""
        from app.modules.data_engineering.interfaces.schedulers.tasks import get_scheduled_tasks

        configs = get_scheduled_tasks()
        sync_task = next((c for c in configs if c.id == "de.sync_stock_daily_increment"), None)
        assert sync_task is not None
        assert sync_task.misfire_grace_time == 7200


class TestCreateTaskCallables:
    """测试 create_task_callables 函数。"""

    def test_returns_async_callable_mapping(self) -> None:
        """验证 create_task_callables() 返回 async callable 映射。"""
        from unittest.mock import MagicMock

        from app.modules.data_engineering.interfaces.schedulers.tasks import create_task_callables

        mock_session_factory = MagicMock()
        callables = create_task_callables(mock_session_factory)

        assert isinstance(callables, dict)
        assert "de.sync_stock_daily_increment" in callables

    def test_callable_is_async(self) -> None:
        """验证返回的 callable 是 async callable。"""
        import asyncio
        from unittest.mock import MagicMock

        from app.modules.data_engineering.interfaces.schedulers.tasks import create_task_callables

        mock_session_factory = MagicMock()
        callables = create_task_callables(mock_session_factory)

        task_callable = callables["de.sync_stock_daily_increment"]
        assert asyncio.iscoroutinefunction(task_callable)


class TestCreateScheduledTasks:
    """测试 create_scheduled_tasks 入口函数。"""

    def test_returns_configs_and_callables_tuple(self) -> None:
        """验证 create_scheduled_tasks() 返回 (configs, task_callables) 元组。"""
        from unittest.mock import MagicMock

        from app.modules.data_engineering.interfaces.schedulers import create_scheduled_tasks

        mock_session_factory = MagicMock()
        result = create_scheduled_tasks(mock_session_factory)

        assert isinstance(result, tuple)
        assert len(result) == 2
        configs, task_callables = result
        assert isinstance(configs, list)
        assert isinstance(task_callables, dict)
