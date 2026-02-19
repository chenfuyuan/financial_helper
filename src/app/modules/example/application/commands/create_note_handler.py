from uuid import UUID

from app.modules.example.domain.note import Note
from app.modules.example.domain.note_repository import NoteRepository
from app.shared_kernel.application.command_handler import CommandHandler

from .create_note import CreateNoteCommand


class CreateNoteHandler(CommandHandler[CreateNoteCommand, UUID]):
    def __init__(self, repository: NoteRepository) -> None:
        self._repository = repository

    async def handle(self, command: CreateNoteCommand) -> UUID:
        note = Note.create(title=command.title, content=command.content)
        await self._repository.save(note)
        return note.id
