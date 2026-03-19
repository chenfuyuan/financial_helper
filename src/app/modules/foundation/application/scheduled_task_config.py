"""调度任务配置相关类。

提供 CronTrigger（cron 触发器值对象）和 ScheduledTaskConfig（任务配置类）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _validate_range(value: int, name: str, min_val: int, max_val: int) -> None:
    """校验数值范围。

    Args:
        value: 待校验的值。
        name: 字段名称（用于错误信息）。
        min_val: 最小值（含）。
        max_val: 最大值（含）。

    Raises:
        ValueError: 当值不在有效范围内时抛出。
    """
    if not (min_val <= value <= max_val):
        raise ValueError(f"{name} must be between {min_val} and {max_val}, got {value}")


@dataclass(frozen=True)
class CronTrigger:
    """Cron 触发器值对象，用于配置任务执行时间。

    支持 cron 表达式的常用字段：小时、分钟、秒、星期几、日期、月份。
    在 __post_init__ 中校验字段范围，提前暴露配置错误。

    Attributes:
        hour: 小时（0-23）。
        minute: 分钟（0-59）。
        second: 秒（0-59），默认为 0。
        day_of_week: 星期几（cron 格式，如 'mon'、'mon-fri'），默认为 None（表示每天）。
        day: 日期（1-31），默认为 None。
        month: 月份（1-12），默认为 None。
    """

    hour: int
    minute: int
    second: int = 0
    day_of_week: str | None = None
    day: int | None = None
    month: int | None = None

    def __post_init__(self) -> None:
        """初始化后校验字段范围。"""
        _validate_range(self.hour, "hour", 0, 23)
        _validate_range(self.minute, "minute", 0, 59)
        _validate_range(self.second, "second", 0, 59)
        if self.day is not None:
            _validate_range(self.day, "day", 1, 31)
        if self.month is not None:
            _validate_range(self.month, "month", 1, 12)

    def to_cron_kwargs(self) -> dict[str, Any]:
        """转换为 APScheduler CronTrigger 的参数格式。

        Returns:
            适配 APScheduler CronTrigger 的关键字参数字典。
        """
        kwargs: dict[str, Any] = {
            "hour": self.hour,
            "minute": self.minute,
            "second": self.second,
        }
        if self.day_of_week is not None:
            kwargs["day_of_week"] = self.day_of_week
        if self.day is not None:
            kwargs["day"] = self.day
        if self.month is not None:
            kwargs["month"] = self.month
        return kwargs


@dataclass(frozen=True)
class ScheduledTaskConfig:
    """调度任务配置类，包含任务执行所需的所有配置信息。

    Attributes:
        id: 任务唯一标识符（如 'de.sync_stock_daily_increment'）。
        trigger: Cron 触发器，定义任务执行时间。
        name: 任务显示名称（如 '同步股票日线'）。
        module: 所属模块名（如 'data_engineering'）。
        max_instances: 最大并发实例数，默认为 1（防止任务重叠）。
        coalesce: 是否合并错过的执行，默认为 True。
        misfire_grace_time: 补执行时间窗口（秒），默认为 7200（2 小时）。
    """

    id: str
    trigger: CronTrigger
    name: str
    module: str
    max_instances: int = 1
    coalesce: bool = True
    misfire_grace_time: int = 7200
