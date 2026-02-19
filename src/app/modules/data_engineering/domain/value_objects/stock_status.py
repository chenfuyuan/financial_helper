"""上市状态值对象。"""

from enum import StrEnum


class StockStatus(StrEnum):
    """上市状态。"""

    LISTED = "L"
    DELISTED = "D"
    SUSPENDED = "P"
