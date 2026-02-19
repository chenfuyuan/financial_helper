"""Fixtures for API (interface) tests. Use in-memory SQLite, no real DB."""

import os

import pytest
from httpx import ASGITransport, AsyncClient

# 在导入 app 前设置，确保测试用 SQLite（纯内存，不落盘）
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")


def _register_handlers(mediator, db):
    """与 main 中一致：注册 example 模块的 command/query handlers。"""
    from app.modules.example.application.commands.create_note import CreateNoteCommand
    from app.modules.example.application.commands.create_note_handler import (
        CreateNoteHandler,
    )
    from app.modules.example.application.queries.get_note import GetNoteQuery
    from app.modules.example.application.queries.get_note_handler import GetNoteHandler
    from app.modules.example.infrastructure.sqlalchemy_note_repository import (
        SqlAlchemyNoteRepository,
    )

    def create_note_handler():
        session = db.session_factory()
        return CreateNoteHandler(repository=SqlAlchemyNoteRepository(session))

    def get_note_handler():
        session = db.session_factory()
        return GetNoteHandler(repository=SqlAlchemyNoteRepository(session))

    mediator.register_command_handler(CreateNoteCommand, create_note_handler)
    mediator.register_query_handler(GetNoteQuery, get_note_handler)


@pytest.fixture
async def api_client():
    """FastAPI 应用 + 内存 SQLite，可调 HTTP 接口。不跑真实 lifespan，直接注入 db/mediator。"""
    import app.modules.example.infrastructure.models  # noqa: F401
    from app.interfaces import main
    from app.shared_kernel.application.mediator import Mediator
    from app.shared_kernel.infrastructure.database import Base, Database

    app = main.app
    db = Database(url=os.environ["DATABASE_URL"], echo=False)
    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    mediator = Mediator()
    _register_handlers(mediator, db)

    app.state.db = db
    app.state.mediator = mediator

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    await db.dispose()
