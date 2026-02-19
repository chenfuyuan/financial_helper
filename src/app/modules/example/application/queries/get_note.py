from dataclasses import dataclass
from uuid import UUID

from app.shared_kernel.application.query import Query


@dataclass(frozen=True)
class GetNoteQuery(Query):
    note_id: UUID | None = None
