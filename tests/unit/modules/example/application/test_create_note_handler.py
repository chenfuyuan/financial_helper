from unittest.mock import AsyncMock

from app.modules.example.application.commands.create_note import CreateNoteCommand
from app.modules.example.application.commands.create_note_handler import CreateNoteHandler
from app.modules.example.domain.note_repository import NoteRepository


class TestCreateNoteHandler:
    async def test_creates_and_saves_note(self) -> None:
        repo = AsyncMock(spec=NoteRepository)
        handler = CreateNoteHandler(repository=repo)

        result = await handler.handle(CreateNoteCommand(title="Test", content="Body"))

        assert result is not None
        repo.save.assert_called_once()
        saved_note = repo.save.call_args[0][0]
        assert saved_note.title == "Test"
        assert saved_note.content == "Body"
