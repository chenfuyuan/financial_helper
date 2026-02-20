from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.shared_kernel.domain.unit_of_work import UnitOfWork


class SqlAlchemyUnitOfWork(UnitOfWork):
    """UoW 只管理事务边界（begin/commit/rollback），session 生命周期由外部（get_uow）管理。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __aenter__(self) -> Self:
        # 不重新创建 session，只开启一个新事务
        await self.session.begin_nested()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        if exc_type:
            await self.rollback()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()


class SqlAlchemyUnitOfWorkFactory:
    """由 session_factory 构造 UoW，供 get_uow 深度依赖注入使用。"""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    def create_session(self) -> AsyncSession:
        return self._session_factory()
