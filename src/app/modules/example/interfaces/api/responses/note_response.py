from uuid import UUID

from pydantic import BaseModel


class NoteResponse(BaseModel):
    id: UUID
    title: str
    content: str
