from dataclasses import dataclass
from uuid import UUID, uuid4

from app.shared_kernel.domain.aggregate_root import AggregateRoot

from .note_created import NoteCreated


@dataclass(eq=False)
class Note(AggregateRoot[UUID]):
    title: str = ""
    content: str = ""

    @classmethod
    def create(cls, title: str, content: str) -> "Note":
        if not title.strip():
            raise ValueError("Note title must not be empty")
        note = cls(id=uuid4(), title=title, content=content)
        note.add_event(NoteCreated(note_id=note.id, title=title))
        return note
