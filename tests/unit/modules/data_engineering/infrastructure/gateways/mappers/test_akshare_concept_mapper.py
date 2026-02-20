from datetime import UTC, datetime

import pandas as pd
import pytest

from app.modules.data_engineering.domain.exceptions import ExternalConceptServiceError
from app.modules.data_engineering.domain.value_objects.data_source import DataSource
from app.modules.data_engineering.infrastructure.gateways.mappers.akshare_concept_mapper import (
    AkShareConceptMapper,
)


def test_rows_to_concepts_maps_fields_and_hash() -> None:
    mapper = AkShareConceptMapper()
    now = datetime.now(UTC)
    df = pd.DataFrame(
        [
            {"板块名称": "人工智能", "板块代码": "BK0818"},
            {"板块名称": "新能源车", "板块代码": "BK0917"},
        ]
    )

    concepts = mapper.rows_to_concepts(df, now=now)

    assert len(concepts) == 2
    assert concepts[0].source == DataSource.AKSHARE
    assert concepts[0].third_code == "BK0818"
    assert concepts[0].name == "人工智能"
    assert concepts[0].content_hash == concepts[0].compute_hash(
        DataSource.AKSHARE,
        "BK0818",
        "人工智能",
    )


def test_rows_to_concepts_raises_for_missing_required_field() -> None:
    mapper = AkShareConceptMapper()
    df = pd.DataFrame([{"板块名称": "人工智能"}])

    with pytest.raises(ExternalConceptServiceError, match="板块代码"):
        mapper.rows_to_concepts(df)


def test_rows_to_stock_tuples_maps_and_validates() -> None:
    mapper = AkShareConceptMapper()
    df = pd.DataFrame([{"代码": "000001", "名称": "平安银行"}])

    stocks = mapper.rows_to_stock_tuples(df)

    assert stocks == [("000001", "平安银行")]
