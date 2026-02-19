from dataclasses import dataclass
from uuid import UUID

from app.modules.example.domain.note_repository import NoteRepository
from app.shared_kernel.application.query_handler import QueryHandler
from app.shared_kernel.domain.exception import NotFoundException, ValidationException

from .get_note import GetNoteQuery


@dataclass
class NoteReadModel:
    id: UUID
    title: str
    content: str


class GetNoteHandler(QueryHandler[GetNoteQuery, NoteReadModel]):
    def __init__(self, repository: NoteRepository) -> None:
        self._repository = repository

    async def handle(self, query: GetNoteQuery) -> NoteReadModel:
        if query.note_id is None:
            raise ValidationException("note_id is required")
        note = await self._repository.find_by_id(query.note_id)
        if note is None:
            raise NotFoundException(f"Note {query.note_id} not found")
        return NoteReadModel(id=note.id, title=note.title, content=note.content)
