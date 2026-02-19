import pytest

from app.modules.example.domain.note import Note
from app.modules.example.domain.note_created import NoteCreated


class TestNote:
    def test_create_note(self) -> None:
        note = Note.create(title="Hello", content="World")
        assert note.title == "Hello"
        assert note.content == "World"
        assert note.id is not None

    def test_create_emits_event(self) -> None:
        note = Note.create(title="Hello", content="World")
        events = note.collect_events()
        assert len(events) == 1
        assert isinstance(events[0], NoteCreated)
        assert events[0].note_id == note.id

    def test_create_empty_title_raises(self) -> None:
        with pytest.raises(ValueError, match="title"):
            Note.create(title="", content="World")
