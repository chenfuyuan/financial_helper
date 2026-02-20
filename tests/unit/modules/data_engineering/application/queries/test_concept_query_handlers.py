from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.modules.data_engineering.application.queries.get_concept_stocks import GetConceptStocks
from app.modules.data_engineering.application.queries.get_concept_stocks_handler import (
    GetConceptStocksHandler,
)
from app.modules.data_engineering.application.queries.get_concepts import GetConcepts
from app.modules.data_engineering.application.queries.get_concepts_handler import (
    GetConceptsHandler,
)
from app.modules.data_engineering.domain.entities.concept import Concept
from app.modules.data_engineering.domain.entities.concept_stock import ConceptStock
from app.modules.data_engineering.domain.exceptions import ConceptNotFoundError
from app.modules.data_engineering.domain.value_objects.data_source import DataSource


def _make_concept(concept_id: int = 1) -> Concept:
    return Concept(
        id=concept_id,
        source=DataSource.AKSHARE,
        third_code="BK0818",
        name="人工智能",
        content_hash=Concept.compute_hash(DataSource.AKSHARE, "BK0818", "人工智能"),
        last_synced_at=datetime.now(UTC),
    )


def _make_concept_stock(concept_id: int = 1) -> ConceptStock:
    return ConceptStock(
        id=1,
        concept_id=concept_id,
        source=DataSource.AKSHARE,
        stock_third_code="000001",
        stock_symbol="000001.SZ",
        content_hash=ConceptStock.compute_hash(DataSource.AKSHARE, "000001", "000001.SZ"),
        added_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_get_concepts_returns_list() -> None:
    concept_repo = AsyncMock()
    concept_repo.find_all = AsyncMock(return_value=[_make_concept()])
    handler = GetConceptsHandler(concept_repo)

    result = await handler.handle(GetConcepts())

    assert len(result) == 1


@pytest.mark.asyncio
async def test_get_concepts_returns_empty_list() -> None:
    concept_repo = AsyncMock()
    concept_repo.find_all = AsyncMock(return_value=[])
    handler = GetConceptsHandler(concept_repo)

    result = await handler.handle(GetConcepts())

    assert result == []


@pytest.mark.asyncio
async def test_get_concept_stocks_returns_list() -> None:
    concept_repo = AsyncMock()
    concept_repo.find_by_id = AsyncMock(return_value=_make_concept())
    concept_stock_repo = AsyncMock()
    concept_stock_repo.find_by_concept_id = AsyncMock(return_value=[_make_concept_stock()])
    handler = GetConceptStocksHandler(concept_repo, concept_stock_repo)

    result = await handler.handle(GetConceptStocks(concept_id=1))

    assert len(result) == 1


@pytest.mark.asyncio
async def test_get_concept_stocks_raises_not_found() -> None:
    concept_repo = AsyncMock()
    concept_repo.find_by_id = AsyncMock(return_value=None)
    concept_stock_repo = AsyncMock()
    handler = GetConceptStocksHandler(concept_repo, concept_stock_repo)

    with pytest.raises(ConceptNotFoundError):
        await handler.handle(GetConceptStocks(concept_id=999))
