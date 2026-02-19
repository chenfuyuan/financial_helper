"""应用层 DTO 基类。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DTO:
    """数据传输对象基类。"""

    pass
