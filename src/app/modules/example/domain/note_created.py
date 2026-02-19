from dataclasses import dataclass
from uuid import UUID

from app.shared_kernel.domain.domain_event import DomainEvent


@dataclass(frozen=True)
class NoteCreated(DomainEvent):
    note_id: UUID | None = None
    title: str = ""
