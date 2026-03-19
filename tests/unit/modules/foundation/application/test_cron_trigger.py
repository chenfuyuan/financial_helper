"""CronTrigger 值对象单元测试。"""

import pytest


class TestCronTriggerDefaultValues:
    """测试 CronTrigger 默认值。"""

    def test_second_defaults_to_zero(self) -> None:
        """验证 CronTrigger(hour=16, minute=30) 的 second 默认为 0。"""
        from app.modules.foundation.application.scheduled_task_config import CronTrigger

        trigger = CronTrigger(hour=16, minute=30)
        assert trigger.second == 0

    def test_hour_and_minute_stored_correctly(self) -> None:
        """验证 hour 和 minute 正确存储。"""
        from app.modules.foundation.application.scheduled_task_config import CronTrigger

        trigger = CronTrigger(hour=16, minute=30)
        assert trigger.hour == 16
        assert trigger.minute == 30


class TestCronTriggerValidation:
    """测试 CronTrigger 参数校验。"""

    def test_invalid_hour_raises_value_error(self) -> None:
        """验证 CronTrigger(hour=25) 抛出 ValueError。"""
        from app.modules.foundation.application.scheduled_task_config import CronTrigger

        with pytest.raises(ValueError, match="hour.*0.*23"):
            CronTrigger(hour=25, minute=30)

    def test_invalid_minute_raises_value_error(self) -> None:
        """验证 CronTrigger(minute=60) 抛出 ValueError。"""
        from app.modules.foundation.application.scheduled_task_config import CronTrigger

        with pytest.raises(ValueError, match="minute.*0.*59"):
            CronTrigger(hour=16, minute=60)

    def test_invalid_second_raises_value_error(self) -> None:
        """验证 CronTrigger(second=60) 抛出 ValueError。"""
        from app.modules.foundation.application.scheduled_task_config import CronTrigger

        with pytest.raises(ValueError, match="second.*0.*59"):
            CronTrigger(hour=16, minute=30, second=60)

    def test_negative_hour_raises_value_error(self) -> None:
        """验证负数 hour 抛出 ValueError。"""
        from app.modules.foundation.application.scheduled_task_config import CronTrigger

        with pytest.raises(ValueError, match="hour.*0.*23"):
            CronTrigger(hour=-1, minute=30)


class TestCronTriggerDayOfWeek:
    """测试 CronTrigger day_of_week 支持。"""

    def test_day_of_week_stored_correctly(self) -> None:
        """验证 CronTrigger(day_of_week='mon') 正确存储。"""
        from app.modules.foundation.application.scheduled_task_config import CronTrigger

        trigger = CronTrigger(hour=9, minute=0, day_of_week="mon")
        assert trigger.day_of_week == "mon"

    def test_day_of_week_defaults_to_none(self) -> None:
        """验证 day_of_week 默认为 None（表示每天）。"""
        from app.modules.foundation.application.scheduled_task_config import CronTrigger

        trigger = CronTrigger(hour=16, minute=30)
        assert trigger.day_of_week is None


class TestCronTriggerImmutability:
    """测试 CronTrigger 不可变性。"""

    def test_cron_trigger_is_frozen(self) -> None:
        """验证 CronTrigger 是 frozen dataclass，不可修改。"""
        from app.modules.foundation.application.scheduled_task_config import CronTrigger

        trigger = CronTrigger(hour=16, minute=30)
        with pytest.raises(AttributeError):
            trigger.hour = 17  # type: ignore[misc]
