"""ScheduledTaskConfig 配置类单元测试。"""

import pytest

from app.modules.foundation.application.scheduled_task_config import CronTrigger, ScheduledTaskConfig


class TestScheduledTaskConfig:
    """测试 ScheduledTaskConfig 配置类。"""

    def test_create_config_with_required_fields(self) -> None:
        """验证创建配置对象包含所有必填字段。"""
        trigger = CronTrigger(hour=16, minute=30)
        config = ScheduledTaskConfig(
            id="de.sync_stock_daily_increment",
            trigger=trigger,
            name="同步股票日线",
            module="data_engineering",
        )

        assert config.id == "de.sync_stock_daily_increment"
        assert config.trigger == trigger
        assert config.name == "同步股票日线"
        assert config.module == "data_engineering"

    def test_misfire_grace_time_defaults_to_7200(self) -> None:
        """验证 misfire_grace_time 默认值为 7200。"""
        trigger = CronTrigger(hour=16, minute=30)
        config = ScheduledTaskConfig(
            id="test.task",
            trigger=trigger,
            name="测试任务",
            module="test",
        )

        assert config.misfire_grace_time == 7200

    def test_max_instances_defaults_to_1(self) -> None:
        """验证 max_instances 默认值为 1。"""
        trigger = CronTrigger(hour=16, minute=30)
        config = ScheduledTaskConfig(
            id="test.task",
            trigger=trigger,
            name="测试任务",
            module="test",
        )

        assert config.max_instances == 1

    def test_coalesce_defaults_to_true(self) -> None:
        """验证 coalesce 默认值为 True。"""
        trigger = CronTrigger(hour=16, minute=30)
        config = ScheduledTaskConfig(
            id="test.task",
            trigger=trigger,
            name="测试任务",
            module="test",
        )

        assert config.coalesce is True

    def test_config_is_frozen(self) -> None:
        """验证配置对象不可变（frozen）。"""
        trigger = CronTrigger(hour=16, minute=30)
        config = ScheduledTaskConfig(
            id="test.task",
            trigger=trigger,
            name="测试任务",
            module="test",
        )

        with pytest.raises(AttributeError):
            config.name = "修改名称"  # type: ignore[misc]

    def test_custom_misfire_grace_time(self) -> None:
        """验证可以自定义 misfire_grace_time。"""
        trigger = CronTrigger(hour=16, minute=30)
        config = ScheduledTaskConfig(
            id="test.task",
            trigger=trigger,
            name="测试任务",
            module="test",
            misfire_grace_time=3600,
        )

        assert config.misfire_grace_time == 3600

    def test_custom_max_instances(self) -> None:
        """验证可以自定义 max_instances。"""
        trigger = CronTrigger(hour=16, minute=30)
        config = ScheduledTaskConfig(
            id="test.task",
            trigger=trigger,
            name="测试任务",
            module="test",
            max_instances=3,
        )

        assert config.max_instances == 3
