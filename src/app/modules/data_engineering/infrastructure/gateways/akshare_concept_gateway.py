"""AKShare 概念网关实现。"""

import asyncio

from app.modules.data_engineering.domain.entities.concept import Concept
from app.modules.data_engineering.domain.exceptions import ExternalConceptServiceError
from app.modules.data_engineering.domain.gateways.concept_gateway import ConceptGateway
from app.modules.data_engineering.infrastructure.gateways.mappers.akshare_concept_mapper import (
    AkShareConceptMapper,
)


class AkShareConceptGateway(ConceptGateway):
    def __init__(self, mapper: AkShareConceptMapper | None = None) -> None:
        self._mapper = mapper or AkShareConceptMapper()

    async def fetch_concepts(self) -> list[Concept]:
        try:
            import akshare as ak  # type: ignore[import-untyped]

            df = await asyncio.to_thread(ak.stock_board_concept_name_em)
            return self._mapper.rows_to_concepts(df)
        except ExternalConceptServiceError:
            raise
        except Exception as exc:
            raise ExternalConceptServiceError(
                f"Failed to fetch concepts from AKShare: {exc}"
            ) from exc

    async def fetch_concept_stocks(
        self, concept_third_code: str, concept_name: str
    ) -> list[tuple[str, str]]:
        try:
            import akshare as ak  # type: ignore[import-untyped]

            df = await asyncio.to_thread(ak.stock_board_concept_cons_em, symbol=concept_name)
            return self._mapper.rows_to_stock_tuples(df)
        except ExternalConceptServiceError:
            raise
        except Exception as exc:
            raise ExternalConceptServiceError(
                f"Failed to fetch concept stocks from AKShare for {concept_third_code}: {exc}"
            ) from exc
