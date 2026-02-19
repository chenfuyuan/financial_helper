from uuid import UUID

from fastapi import APIRouter, Depends

from app.interfaces.dependencies import get_mediator, get_uow
from app.interfaces.response import ApiResponse
from app.modules.example.application.commands.create_note import CreateNoteCommand
from app.modules.example.application.commands.create_note_handler import CreateNoteHandler
from app.modules.example.application.queries.get_note import GetNoteQuery
from app.modules.example.infrastructure.sqlalchemy_note_repository import SqlAlchemyNoteRepository
from app.shared_kernel.application.mediator import Mediator
from app.shared_kernel.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork

from .requests.create_note_request import CreateNoteRequest
from .responses.note_response import NoteResponse

router = APIRouter(prefix="/notes", tags=["notes"])


@router.post("", response_model=ApiResponse[dict])
async def create_note(
    body: CreateNoteRequest,
    uow: SqlAlchemyUnitOfWork = Depends(get_uow),
) -> ApiResponse[dict]:
    repo = SqlAlchemyNoteRepository(uow.session)
    handler = CreateNoteHandler(repository=repo)
    note_id = await handler.handle(CreateNoteCommand(title=body.title, content=body.content))
    await uow.commit()
    return ApiResponse.success(data={"id": str(note_id)}, message="Note created")


@router.get("/{note_id}", response_model=ApiResponse[NoteResponse])
async def get_note(
    note_id: UUID,
    mediator: Mediator = Depends(get_mediator),
) -> ApiResponse[NoteResponse]:
    result = await mediator.query(GetNoteQuery(note_id=note_id))
    return ApiResponse.success(
        data=NoteResponse(id=result.id, title=result.title, content=result.content)
    )
