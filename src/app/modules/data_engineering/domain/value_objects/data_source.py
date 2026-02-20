"""数据来源值对象。"""

from enum import StrEnum


class DataSource(StrEnum):
    """数据来源。"""

    TUSHARE = "TUSHARE"
    AKSHARE = "AKSHARE"
