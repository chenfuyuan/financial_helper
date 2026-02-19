from pydantic import BaseModel, Field


class CreateNoteRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(default="")
