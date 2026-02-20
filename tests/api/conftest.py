"""Fixtures for API (interface) tests. Use in-memory SQLite, no real DB."""

import os

import pytest
from httpx import ASGITransport, AsyncClient

# 在导入 app 前设置，确保测试用 SQLite（纯内存，不落盘）
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")


def _register_handlers(mediator, db):
    """与 main 中一致：注册各模块的 command/query handlers（当前无通过 Mediator 的 handler）。"""
    pass


@pytest.fixture
async def api_client():
    """FastAPI 应用 + 内存 SQLite，可调 HTTP 接口。不跑真实 lifespan，直接注入 db/mediator。"""
    import app.modules.data_engineering.infrastructure.models  # noqa: F401
    import app.modules.data_engineering.infrastructure.models.concept_model  # noqa: F401
    import app.modules.data_engineering.infrastructure.models.concept_stock_model  # noqa: F401
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
