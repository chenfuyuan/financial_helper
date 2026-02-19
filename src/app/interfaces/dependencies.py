from collections.abc import AsyncGenerator
from typing import cast

from fastapi import Request

from app.shared_kernel.application.mediator import Mediator
from app.shared_kernel.infrastructure.database import Database
from app.shared_kernel.infrastructure.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


def get_db(request: Request) -> Database:
    return cast(Database, request.app.state.db)


def get_mediator(request: Request) -> Mediator:
    return cast(Mediator, request.app.state.mediator)


async def get_uow(request: Request) -> AsyncGenerator[SqlAlchemyUnitOfWork, None]:
    db: Database = request.app.state.db
    async with SqlAlchemyUnitOfWork(db.session_factory) as uow:
        yield uow
