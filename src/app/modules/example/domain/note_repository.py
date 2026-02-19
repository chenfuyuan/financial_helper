from abc import abstractmethod
from uuid import UUID

from app.shared_kernel.domain.repository import Repository

from .note import Note


class NoteRepository(Repository[Note, UUID]):
    @abstractmethod
    async def find_by_id(self, id: UUID) -> Note | None:
        pass

    @abstractmethod
    async def save(self, aggregate: Note) -> None:
        pass

    @abstractmethod
    async def delete(self, aggregate: Note) -> None:
        pass
