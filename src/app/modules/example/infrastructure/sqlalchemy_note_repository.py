from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.example.domain.note import Note
from app.modules.example.domain.note_repository import NoteRepository
from app.shared_kernel.infrastructure.sqlalchemy_repository import SqlAlchemyRepository

from .models.note_model import NoteModel


class SqlAlchemyNoteRepository(SqlAlchemyRepository[Note, UUID], NoteRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, NoteModel)

    def _to_entity(self, model: Any) -> Note:
        return Note(id=model.id, title=model.title, content=model.content)

    def _to_model(self, entity: Note) -> Any:
        return NoteModel(id=entity.id, title=entity.title, content=entity.content)
