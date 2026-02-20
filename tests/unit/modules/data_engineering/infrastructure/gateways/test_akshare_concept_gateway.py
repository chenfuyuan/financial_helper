from unittest.mock import patch

import pandas as pd
import pytest

from app.modules.data_engineering.domain.exceptions import ExternalConceptServiceError
from app.modules.data_engineering.infrastructure.gateways.akshare_concept_gateway import (
    AkShareConceptGateway,
)


@pytest.mark.asyncio
@patch("app.modules.data_engineering.infrastructure.gateways.akshare_concept_gateway.asyncio.to_thread")
async def test_fetch_concepts_success(mock_to_thread) -> None:
    mock_to_thread.return_value = pd.DataFrame([{"板块名称": "人工智能", "板块代码": "BK0818"}])
    gateway = AkShareConceptGateway()

    concepts = await gateway.fetch_concepts()

    assert len(concepts) == 1
    assert concepts[0].third_code == "BK0818"


@pytest.mark.asyncio
@patch("app.modules.data_engineering.infrastructure.gateways.akshare_concept_gateway.asyncio.to_thread")
async def test_fetch_concept_stocks_success(mock_to_thread) -> None:
    mock_to_thread.return_value = pd.DataFrame([{"代码": "000001", "名称": "平安银行"}])
    gateway = AkShareConceptGateway()

    stocks = await gateway.fetch_concept_stocks("BK0818", "人工智能")

    assert stocks == [("000001", "平安银行")]


@pytest.mark.asyncio
@patch("app.modules.data_engineering.infrastructure.gateways.akshare_concept_gateway.asyncio.to_thread")
async def test_fetch_concepts_wraps_external_errors(mock_to_thread) -> None:
    mock_to_thread.side_effect = RuntimeError("boom")
    gateway = AkShareConceptGateway()

    with pytest.raises(ExternalConceptServiceError, match="fetch concepts"):
        await gateway.fetch_concepts()


@pytest.mark.asyncio
@patch("app.modules.data_engineering.infrastructure.gateways.akshare_concept_gateway.asyncio.to_thread")
async def test_fetch_concept_stocks_wraps_external_errors(mock_to_thread) -> None:
    mock_to_thread.side_effect = RuntimeError("boom")
    gateway = AkShareConceptGateway()

    with pytest.raises(ExternalConceptServiceError, match="fetch concept stocks"):
        await gateway.fetch_concept_stocks("BK0818", "人工智能")
