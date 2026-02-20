from datetime import UTC, datetime
from hashlib import sha256

from app.modules.data_engineering.domain.entities.concept import Concept
from app.modules.data_engineering.domain.entities.concept_stock import ConceptStock
from app.modules.data_engineering.domain.value_objects.data_source import DataSource


def test_concept_hash_computation() -> None:
    # 1. 直接计算函数结果正确
    hash_value = Concept.calculate_content_hash(DataSource.AKSHARE, "BK0818", "人工智能")
    expected = sha256("AKSHARE|BK0818|人工智能".encode("utf-8")).hexdigest()[:16]
    assert hash_value == expected

    # 2. 字段相同时哈希值相同
    now = datetime.now(UTC)
    concept = Concept(
        id=None,
        source=DataSource.AKSHARE,
        third_code="BK0818",
        name="人工智能",
        content_hash=Concept.calculate_content_hash(DataSource.AKSHARE, "BK0818", "人工智能"),
        last_synced_at=now,
    )
    concept2 = Concept(
        id=None,
        source=DataSource.AKSHARE,
        third_code="BK0818",
        name="人工智能",
        content_hash=Concept.calculate_content_hash(DataSource.AKSHARE, "BK0818", "人工智能"),
        last_synced_at=now,
    )
    assert concept.content_hash == concept2.content_hash

    # 3. 字段不同时哈希值不同
    hash3 = Concept.calculate_content_hash(DataSource.AKSHARE, "BK0999", "人工智能")
    assert concept.content_hash != hash3


def test_concept_stock_hash_computation() -> None:
    # 4. stock_symbol 参与哈希计算
    hash1 = ConceptStock.calculate_content_hash(DataSource.AKSHARE, "000001", "000001.SZ")
    hash2 = ConceptStock.calculate_content_hash(DataSource.AKSHARE, "000001", "000001.SZ")
    assert hash1 == hash2

    # 5. stock_symbol 变化会导致哈希变化；None 时按空字符串处理
    hash3 = ConceptStock.calculate_content_hash(DataSource.AKSHARE, "000001", None)
    assert hash1 != hash3
