from unittest.mock import AsyncMock, patch

import pytest

from app.modules.data_engineering.domain.entities.concept import Concept
from app.modules.data_engineering.domain.value_objects.data_source import DataSource


def _make_concept() -> Concept:
    from datetime import UTC, datetime

    return Concept(
        id=None,
        source=DataSource.AKSHARE,
        third_code="BK0818",
        name="人工智能",
        content_hash=Concept.compute_hash(DataSource.AKSHARE, "BK0818", "人工智能"),
        last_synced_at=datetime.now(UTC),
    )


class TestConceptRouter:
    @pytest.mark.asyncio
    async def test_sync_and_list_concepts(self, api_client) -> None:
        with patch("app.modules.data_engineering.interfaces.dependencies.AkShareConceptGateway") as MockGateway:
            MockGateway.return_value.fetch_concepts = AsyncMock(return_value=[_make_concept()])
            MockGateway.return_value.fetch_concept_stocks = AsyncMock(return_value=[])

            sync_resp = await api_client.post("/api/v1/data-engineering/concepts/sync")

        assert sync_resp.status_code == 200
        sync_body = sync_resp.json()
        assert sync_body["code"] == 200
        assert sync_body["data"]["new_concepts"] == 1

        list_resp = await api_client.get("/api/v1/data-engineering/concepts")
        assert list_resp.status_code == 200
        list_body = list_resp.json()
        assert list_body["code"] == 200
        assert isinstance(list_body["data"], list)

    @pytest.mark.asyncio
    async def test_get_concept_stocks_not_found_returns_404(self, api_client) -> None:
        response = await api_client.get("/api/v1/data-engineering/concepts/999/stocks")

        assert response.status_code == 404
