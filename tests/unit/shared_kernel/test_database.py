from app.shared_kernel.infrastructure.database import Database


class TestDatabase:
    def test_creates_engine(self) -> None:
        db = Database(url="sqlite+aiosqlite:///:memory:")
        assert db.session_factory is not None

    async def test_dispose(self) -> None:
        db = Database(url="sqlite+aiosqlite:///:memory:")
        await db.dispose()
