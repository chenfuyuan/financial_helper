"""概念板块相关 API。"""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.interfaces.response import ApiResponse
from app.modules.data_engineering.application.commands.sync_concepts import SyncConcepts
from app.modules.data_engineering.application.commands.sync_concepts_handler import (
    SyncConceptsHandler,
)
from app.modules.data_engineering.application.queries.get_concept_stocks import (
    GetConceptStocks,
)
from app.modules.data_engineering.application.queries.get_concept_stocks_handler import (
    GetConceptStocksHandler,
)
from app.modules.data_engineering.application.queries.get_concepts import GetConcepts
from app.modules.data_engineering.application.queries.get_concepts_handler import (
    GetConceptsHandler,
)
from app.modules.data_engineering.domain.value_objects.data_source import DataSource
from app.modules.data_engineering.interfaces.dependencies import (
    get_get_concept_stocks_handler,
    get_get_concepts_handler,
    get_sync_concepts_handler,
)

router = APIRouter(prefix="/data-engineering/concepts", tags=["data_engineering"])


class SyncConceptsResponse(BaseModel):
    total_concepts: int
    new_concepts: int
    modified_concepts: int
    deleted_concepts: int
    total_stocks: int
    new_stocks: int
    modified_stocks: int
    deleted_stocks: int
    duration_ms: int


class ConceptResponse(BaseModel):
    id: int
    source: str
    third_code: str
    name: str
    last_synced_at: datetime


class ConceptStockResponse(BaseModel):
    id: int
    concept_id: int
    source: str
    stock_third_code: str
    stock_symbol: str | None
    added_at: datetime


@router.post("/sync", response_model=ApiResponse[SyncConceptsResponse])
async def sync_concepts(
    handler: SyncConceptsHandler = Depends(get_sync_concepts_handler),
) -> ApiResponse[SyncConceptsResponse]:
    result = await handler.handle(SyncConcepts())
    return ApiResponse.success(
        data=SyncConceptsResponse(
            total_concepts=result.total_concepts,
            new_concepts=result.new_concepts,
            modified_concepts=result.modified_concepts,
            deleted_concepts=result.deleted_concepts,
            total_stocks=result.total_stocks,
            new_stocks=result.new_stocks,
            modified_stocks=result.modified_stocks,
            deleted_stocks=result.deleted_stocks,
            duration_ms=result.duration_ms,
        )
    )


@router.get("", response_model=ApiResponse[list[ConceptResponse]])
async def get_concepts(
    source: DataSource | None = Query(default=None),
    handler: GetConceptsHandler = Depends(get_get_concepts_handler),
) -> ApiResponse[list[ConceptResponse]]:
    concepts = await handler.handle(GetConcepts(source=source))
    return ApiResponse.success(
        data=[
            ConceptResponse(
                id=concept.id or 0,
                source=concept.source.value,
                third_code=concept.third_code,
                name=concept.name,
                last_synced_at=concept.last_synced_at,
            )
            for concept in concepts
        ]
    )


@router.get("/{concept_id}/stocks", response_model=ApiResponse[list[ConceptStockResponse]])
async def get_concept_stocks(
    concept_id: int,
    handler: GetConceptStocksHandler = Depends(get_get_concept_stocks_handler),
) -> ApiResponse[list[ConceptStockResponse]]:
    rows = await handler.handle(GetConceptStocks(concept_id=concept_id))
    return ApiResponse.success(
        data=[
            ConceptStockResponse(
                id=row.id or 0,
                concept_id=row.concept_id,
                source=row.source.value,
                stock_third_code=row.stock_third_code,
                stock_symbol=row.stock_symbol,
                added_at=row.added_at,
            )
            for row in rows
        ]
    )
