from datetime import UTC, date, datetime
from unittest.mock import AsyncMock

import pytest

from app.modules.data_engineering.application.commands.sync_concepts import SyncConcepts
from app.modules.data_engineering.application.commands.sync_concepts_handler import (
    SyncConceptsHandler,
)
from app.modules.data_engineering.domain.entities.concept import Concept
from app.modules.data_engineering.domain.entities.concept_stock import ConceptStock
from app.modules.data_engineering.domain.entities.stock_basic import StockBasic
from app.modules.data_engineering.domain.exceptions import ExternalConceptServiceError
from app.modules.data_engineering.domain.value_objects.data_source import DataSource
from app.modules.data_engineering.domain.value_objects.stock_status import StockStatus


def _make_concept(
    third_code: str,
    name: str,
    hash_override: str | None = None,
    concept_id: int | None = None,
) -> Concept:
    return Concept(
        id=concept_id,
        source=DataSource.AKSHARE,
        third_code=third_code,
        name=name,
        content_hash=hash_override or Concept.compute_hash(DataSource.AKSHARE, third_code, name),
        last_synced_at=datetime.now(UTC),
    )


def _make_stock_basic(symbol: str, third_code: str) -> StockBasic:
    return StockBasic(
        id=1,
        source=DataSource.TUSHARE,
        third_code=third_code,
        symbol=symbol,
        name="name",
        market="SZ",
        area="SZ",
        industry="bank",
        list_date=date(2020, 1, 1),
        status=StockStatus.LISTED,
    )


@pytest.mark.asyncio
async def test_handle_new_concept_syncs_stocks() -> None:
    gateway = AsyncMock()
    gateway.fetch_concepts = AsyncMock(return_value=[_make_concept("BK0818", "人工智能")])
    gateway.fetch_concept_stocks = AsyncMock(return_value=[("000001", "平安银行")])
    concept_repo = AsyncMock()
    concept_repo.find_all = AsyncMock(return_value=[])
    concept_repo.save = AsyncMock(return_value=_make_concept("BK0818", "人工智能", concept_id=101))
    stock_repo = AsyncMock()
    stock_repo.find_by_concept_id = AsyncMock(return_value=[])
    stock_basic_repo = AsyncMock()
    stock_basic_repo.find_all_listed = AsyncMock(return_value=[_make_stock_basic("000001.SZ", "000001")])
    uow = AsyncMock()

    handler = SyncConceptsHandler(gateway, concept_repo, stock_repo, stock_basic_repo, uow)
    result = await handler.handle(SyncConcepts())

    assert result.new_concepts == 1
    assert result.new_stocks == 1
    uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_unchanged_concept_skips_stock_sync() -> None:
    concept = _make_concept("BK0818", "人工智能", concept_id=101)
    gateway = AsyncMock()
    gateway.fetch_concepts = AsyncMock(return_value=[concept])
    gateway.fetch_concept_stocks = AsyncMock()
    concept_repo = AsyncMock()
    concept_repo.find_all = AsyncMock(return_value=[concept])
    concept_repo.save = AsyncMock(return_value=concept)
    stock_repo = AsyncMock()
    stock_basic_repo = AsyncMock()
    stock_basic_repo.find_all = AsyncMock(return_value=[])
    uow = AsyncMock()

    handler = SyncConceptsHandler(gateway, concept_repo, stock_repo, stock_basic_repo, uow)
    result = await handler.handle(SyncConcepts())

    assert result.modified_concepts == 0
    gateway.fetch_concept_stocks.assert_not_called()


@pytest.mark.asyncio
async def test_handle_deleted_concept_removes_rows() -> None:
    local = _make_concept("BK0818", "人工智能", concept_id=101)
    gateway = AsyncMock()
    gateway.fetch_concepts = AsyncMock(return_value=[])
    concept_repo = AsyncMock()
    concept_repo.find_all = AsyncMock(return_value=[local])
    stock_repo = AsyncMock()
    stock_basic_repo = AsyncMock()
    stock_basic_repo.find_all = AsyncMock(return_value=[])
    uow = AsyncMock()

    handler = SyncConceptsHandler(gateway, concept_repo, stock_repo, stock_basic_repo, uow)
    result = await handler.handle(SyncConcepts())

    assert result.deleted_concepts == 1
    stock_repo.delete_by_concept_id.assert_awaited_once_with(101)
    concept_repo.delete.assert_awaited_once_with(101)


@pytest.mark.asyncio
async def test_handle_propagates_external_errors() -> None:
    gateway = AsyncMock()
    gateway.fetch_concepts = AsyncMock(side_effect=ExternalConceptServiceError("boom"))
    concept_repo = AsyncMock()
    stock_repo = AsyncMock()
    stock_basic_repo = AsyncMock()
    uow = AsyncMock()
    handler = SyncConceptsHandler(gateway, concept_repo, stock_repo, stock_basic_repo, uow)

    with pytest.raises(ExternalConceptServiceError):
        await handler.handle(SyncConcepts())

    uow.commit.assert_not_called()


@pytest.mark.asyncio
async def test_handle_modified_concept_triggers_stock_incremental_sync() -> None:
    local = _make_concept("BK0818", "人工智能", hash_override="aaaa", concept_id=101)
    remote = _make_concept("BK0818", "人工智能2", hash_override="bbbb", concept_id=101)
    local_stock = ConceptStock(
        id=11,
        concept_id=101,
        source=DataSource.AKSHARE,
        stock_third_code="000001",
        stock_symbol="000001.SZ",
        content_hash=ConceptStock.compute_hash(DataSource.AKSHARE, "000001", "000001.SZ"),
        added_at=datetime.now(UTC),
    )

    gateway = AsyncMock()
    gateway.fetch_concepts = AsyncMock(return_value=[remote])
    gateway.fetch_concept_stocks = AsyncMock(return_value=[("000002", "万科A")])
    concept_repo = AsyncMock()
    concept_repo.find_all = AsyncMock(return_value=[local])
    concept_repo.save = AsyncMock(return_value=remote)
    stock_repo = AsyncMock()
    stock_repo.find_by_concept_id = AsyncMock(return_value=[local_stock])
    stock_basic_repo = AsyncMock()
    stock_basic_repo.find_all = AsyncMock(return_value=[_make_stock_basic("000002.SZ", "000002.SZ")])
    uow = AsyncMock()
    handler = SyncConceptsHandler(gateway, concept_repo, stock_repo, stock_basic_repo, uow)

    result = await handler.handle(SyncConcepts())

    assert result.modified_concepts == 1
    gateway.fetch_concept_stocks.assert_awaited_once()
