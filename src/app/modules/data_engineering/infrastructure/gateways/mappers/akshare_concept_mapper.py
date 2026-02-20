"""AKShare 概念数据映射：DataFrame -> 领域实体。"""

from datetime import UTC, datetime

import pandas as pd

from app.modules.data_engineering.domain.entities.concept import Concept
from app.modules.data_engineering.domain.exceptions import ExternalConceptServiceError
from app.modules.data_engineering.domain.value_objects.data_source import DataSource


def _get_str_value(row: pd.Series, candidates: list[str]) -> str | None:
    for key in candidates:
        if key not in row:
            continue
        value = row.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


class AkShareConceptMapper:
    """将 AKShare DataFrame 行映射为 Concept 和成分股元组。"""

    def rows_to_concepts(self, df: pd.DataFrame, now: datetime | None = None) -> list[Concept]:
        synced_at = now or datetime.now(UTC)
        concepts: list[Concept] = []

        for _, row in df.iterrows():
            third_code = _get_str_value(row, ["板块代码", "代码"])
            name = _get_str_value(row, ["板块名称", "名称"])
            if not third_code:
                raise ExternalConceptServiceError(
                    "AKShare concept row missing required field: 板块代码"
                )
            if not name:
                raise ExternalConceptServiceError(
                    "AKShare concept row missing required field: 板块名称"
                )
            concepts.append(
                Concept(
                    id=None,
                    source=DataSource.AKSHARE,
                    third_code=third_code,
                    name=name,
                    content_hash=Concept.compute_hash(DataSource.AKSHARE, third_code, name),
                    last_synced_at=synced_at,
                )
            )

        return concepts

    def rows_to_stock_tuples(self, df: pd.DataFrame) -> list[tuple[str, str]]:
        stocks: list[tuple[str, str]] = []
        for _, row in df.iterrows():
            stock_third_code = _get_str_value(row, ["代码", "股票代码"])
            stock_name = _get_str_value(row, ["名称", "股票名称"])
            if not stock_third_code:
                raise ExternalConceptServiceError("AKShare stock row missing required field: 代码")
            if not stock_name:
                raise ExternalConceptServiceError("AKShare stock row missing required field: 名称")
            stocks.append((stock_third_code, stock_name))
        return stocks
