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
    """创建一个请求级别的 session，并将其传入 UoW。

    Session 在整个请求生命周期内唯一，UoW 仅管理事务边界，
    从而保证 repository 和 uow.commit() 始终操作同一个 session。
    """
    db: Database = request.app.state.db
    session = db.session_factory()
    try:
        uow = SqlAlchemyUnitOfWork(session)
        yield uow
    finally:
        await session.close()
