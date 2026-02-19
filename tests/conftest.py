from unittest.mock import AsyncMock

import pytest

from app.shared_kernel.domain.unit_of_work import UnitOfWork


@pytest.fixture
def mock_uow() -> AsyncMock:
    uow = AsyncMock(spec=UnitOfWork)
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=None)
    return uow
