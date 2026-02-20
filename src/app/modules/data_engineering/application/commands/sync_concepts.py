"""概念板块同步命令。"""

from dataclasses import dataclass

from app.shared_kernel.application.command import Command


@dataclass(frozen=True)
class SyncConcepts(Command):
    """触发一次概念板块同步。"""

    pass


@dataclass(frozen=True)
class SyncConceptsResult:
    total_concepts: int
    new_concepts: int
    modified_concepts: int
    deleted_concepts: int
    total_stocks: int
    new_stocks: int
    modified_stocks: int
    deleted_stocks: int
    duration_ms: int
