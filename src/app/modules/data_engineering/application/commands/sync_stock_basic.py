"""同步股票基础信息命令。"""

from dataclasses import dataclass

from app.shared_kernel.application.command import Command


@dataclass(frozen=True)
class SyncStockBasic(Command):
    """触发一次从外部数据源拉取并写入本地仓储的同步。"""

    pass
