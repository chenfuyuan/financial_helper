# AKShare 概念板块同步 — 实现计划 Part 1（Task 0-5）

> 接续文件：`plan-part2.md`（Task 6-11）

**Goal:** 在 `data_engineering` 模块新增 AKShare 数据源，实现概念板块两级哈希增量同步及查询 API。

**Architecture:** 四层 DDD（Domain → Infrastructure → Application → Interfaces），单事务提交，参考现有 `StockBasic` / `TuShareStockGateway` 模式。

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy async, akshare≥1.12.0, pytest-asyncio, aiosqlite

**必读：** `openspec/changes/akshare-concept-sync/design.md`、`guide/architecture.md`、`guide/development-conventions.md`、`guide/testing.md`

---

## Task 0: 依赖 + DataSource 枚举扩展

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/app/modules/data_engineering/domain/value_objects/data_source.py`

**Step 1: pyproject.toml** — 在 `[project] dependencies` 追加 `"akshare>=1.12.0",`

**Step 2: DataSource 枚举**
```python
# src/app/modules/data_engineering/domain/value_objects/data_source.py
from enum import StrEnum

class DataSource(StrEnum):
    TUSHARE = "TUSHARE"
    AKSHARE = "AKSHARE"
```

**Step 3: 安装并验证**
```bash
pip install akshare
python -c "from app.modules.data_engineering.domain.value_objects.data_source import DataSource; assert DataSource.AKSHARE == 'AKSHARE'; print('OK')"
```

**Step 4: Commit**
```bash
git add pyproject.toml src/app/modules/data_engineering/domain/value_objects/data_source.py
git commit -m "feat(data_engineering): add akshare dependency and AKSHARE DataSource"
```

---

## Task 1: 领域实体 — Concept + ConceptStock（含哈希静态方法）

**Files:**
- Create: `src/app/modules/data_engineering/domain/entities/concept.py`
- Create: `src/app/modules/data_engineering/domain/entities/concept_stock.py`
- Create: `tests/unit/modules/data_engineering/domain/test_concept_hash.py`

**Step 1: 写失败测试**
```python
# tests/unit/modules/data_engineering/domain/test_concept_hash.py
from hashlib import sha256
from app.modules.data_engineering.domain.entities.concept import Concept
from app.modules.data_engineering.domain.entities.concept_stock import ConceptStock
from app.modules.data_engineering.domain.value_objects.data_source import DataSource

class TestConceptHash:
    def test_compute_hash_sha256_pipe_joined(self) -> None:
        expected = sha256("AKSHARE|BK0818|融资融券".encode()).hexdigest()[:16]
        assert Concept.compute_hash(DataSource.AKSHARE, "BK0818", "融资融券") == expected

    def test_compute_hash_length_is_16(self) -> None:
        assert len(Concept.compute_hash(DataSource.AKSHARE, "BK0001", "测试")) == 16

    def test_different_names_produce_different_hashes(self) -> None:
        assert Concept.compute_hash(DataSource.AKSHARE, "BK0001", "A") != \
               Concept.compute_hash(DataSource.AKSHARE, "BK0001", "B")

class TestConceptStockHash:
    def test_compute_hash_excludes_concept_id(self) -> None:
        expected = sha256("AKSHARE|000001|000001.SZ".encode()).hexdigest()[:16]
        assert ConceptStock.compute_hash(DataSource.AKSHARE, "000001", "000001.SZ") == expected

    def test_none_symbol_uses_empty_string(self) -> None:
        expected = sha256("AKSHARE|000001|".encode()).hexdigest()[:16]
        assert ConceptStock.compute_hash(DataSource.AKSHARE, "000001", None) == expected
```

**Step 2: 运行确认失败**
```bash
pytest tests/unit/modules/data_engineering/domain/test_concept_hash.py -v
```
Expected: `ImportError: cannot import name 'Concept'`

**Step 3: 实现 Concept**
```python
# src/app/modules/data_engineering/domain/entities/concept.py
"""概念板块聚合根。"""
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from app.shared_kernel.domain.aggregate_root import AggregateRoot
from ..value_objects.data_source import DataSource

@dataclass(eq=False)
class Concept(AggregateRoot[int | None]):
    """概念板块聚合根。以 (source, third_code) 为逻辑唯一键，仅含业务属性。

    Attributes:
        id: 主键；新建未持久化时为 None。
        source: 数据来源（如 AKSHARE）。
        third_code: 第三方概念代码（如 BK0818）。
        name: 概念名称。
        content_hash: 基于业务字段的 SHA-256 摘要前16位，用于增量同步变更检测。
        last_synced_at: 最后同步时间。
    """
    id: int | None
    source: DataSource
    third_code: str
    name: str
    content_hash: str
    last_synced_at: datetime

    @staticmethod
    def compute_hash(source: DataSource, third_code: str, name: str) -> str:
        """sha256(source|third_code|name) 前16位。"""
        return sha256(f"{source}|{third_code}|{name}".encode()).hexdigest()[:16]
```

**Step 4: 实现 ConceptStock**
```python
# src/app/modules/data_engineering/domain/entities/concept_stock.py
"""概念-股票关联实体。"""
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from app.shared_kernel.domain.entity import Entity
from ..value_objects.data_source import DataSource

@dataclass(eq=False)
class ConceptStock(Entity[int | None]):
    """概念-股票关联实体。以 (concept_id, source, stock_third_code) 为逻辑唯一键。

    Attributes:
        id: 主键；新建未持久化时为 None。
        concept_id: 关联的 Concept.id。
        source: 数据来源。
        stock_third_code: 股票第三方代码（AKShare 原始代码，如 000001）。
        stock_symbol: 匹配后的 StockBasic.symbol（如 000001.SZ）；匹配失败为 None。
        content_hash: 基于业务字段的 SHA-256 摘要前16位。
        added_at: 关联添加时间。
    """
    id: int | None
    concept_id: int
    source: DataSource
    stock_third_code: str
    stock_symbol: str | None
    content_hash: str
    added_at: datetime

    @staticmethod
    def compute_hash(source: DataSource, stock_third_code: str, stock_symbol: str | None) -> str:
        """sha256(source|stock_third_code|stock_symbol) 前16位。不含 concept_id。"""
        return sha256(f"{source}|{stock_third_code}|{stock_symbol or ''}".encode()).hexdigest()[:16]
```

**Step 5: 运行确认通过**
```bash
pytest tests/unit/modules/data_engineering/domain/test_concept_hash.py -v
```
Expected: 5 tests PASSED

**Step 6: Commit**
```bash
git add src/app/modules/data_engineering/domain/entities/concept.py \
        src/app/modules/data_engineering/domain/entities/concept_stock.py \
        tests/unit/modules/data_engineering/domain/test_concept_hash.py
git commit -m "feat(data_engineering): add Concept/ConceptStock entities with hash computation"
```

---

## Task 2: 领域接口 — 异常、ConceptGateway、仓储接口

**Files:**
- Modify: `src/app/modules/data_engineering/domain/exceptions.py`
- Create: `src/app/modules/data_engineering/domain/gateways/concept_gateway.py`
- Create: `src/app/modules/data_engineering/domain/repositories/concept_repository.py`
- Create: `src/app/modules/data_engineering/domain/repositories/concept_stock_repository.py`

纯抽象接口，无行为可测试，直接实现后验证可导入。

**Step 1: 扩展异常**
```python
# src/app/modules/data_engineering/domain/exceptions.py
from app.shared_kernel.domain.exception import DomainException

class ExternalStockServiceError(DomainException):
    """外部股票数据源拉取或解析失败。"""

class ExternalConceptServiceError(DomainException):
    """AKShare 概念板块数据源拉取或解析失败。"""

class ConceptNotFoundError(DomainException):
    """查询的概念板块不存在。"""
```

**Step 2: ConceptGateway**
```python
# src/app/modules/data_engineering/domain/gateways/concept_gateway.py
from abc import ABC, abstractmethod
from ..entities.concept import Concept

class ConceptGateway(ABC):
    """从外部数据源拉取概念板块及成分股数据。"""

    @abstractmethod
    async def fetch_concepts(self) -> list[Concept]: ...

    @abstractmethod
    async def fetch_concept_stocks(
        self, concept_third_code: str, concept_name: str
    ) -> list[tuple[str, str]]:
        """返回 [(stock_third_code, stock_name), ...]。"""
        ...
```

**Step 3: ConceptRepository**
```python
# src/app/modules/data_engineering/domain/repositories/concept_repository.py
from abc import ABC, abstractmethod
from ..entities.concept import Concept
from ..value_objects.data_source import DataSource

class ConceptRepository(ABC):
    """不 commit，由调用方 UnitOfWork 管理事务。"""

    @abstractmethod
    async def find_all(self, source: DataSource) -> list[Concept]: ...
    @abstractmethod
    async def find_by_id(self, concept_id: int) -> Concept | None: ...
    @abstractmethod
    async def find_by_third_code(self, source: DataSource, third_code: str) -> Concept | None: ...
    @abstractmethod
    async def save(self, concept: Concept) -> Concept:
        """新增或更新，返回含 DB 分配 id 的实体。"""
        ...
    @abstractmethod
    async def delete(self, concept_id: int) -> None: ...
    @abstractmethod
    async def delete_many(self, concept_ids: list[int]) -> None: ...
```

**Step 4: ConceptStockRepository**
```python
# src/app/modules/data_engineering/domain/repositories/concept_stock_repository.py
from abc import ABC, abstractmethod
from ..entities.concept_stock import ConceptStock

class ConceptStockRepository(ABC):
    """不 commit，由调用方 UnitOfWork 管理事务。"""

    @abstractmethod
    async def find_by_concept_id(self, concept_id: int) -> list[ConceptStock]: ...
    @abstractmethod
    async def save_many(self, concept_stocks: list[ConceptStock]) -> None: ...
    @abstractmethod
    async def delete_many(self, concept_stock_ids: list[int]) -> None: ...
    @abstractmethod
    async def delete_by_concept_id(self, concept_id: int) -> None: ...
```

**Step 5: 验证可导入**
```bash
python -c "
from app.modules.data_engineering.domain.exceptions import ExternalConceptServiceError, ConceptNotFoundError
from app.modules.data_engineering.domain.gateways.concept_gateway import ConceptGateway
from app.modules.data_engineering.domain.repositories.concept_repository import ConceptRepository
from app.modules.data_engineering.domain.repositories.concept_stock_repository import ConceptStockRepository
print('Domain interfaces OK')
"
```

**Step 6: Commit**
```bash
git add src/app/modules/data_engineering/domain/exceptions.py \
        src/app/modules/data_engineering/domain/gateways/concept_gateway.py \
        src/app/modules/data_engineering/domain/repositories/concept_repository.py \
        src/app/modules/data_engineering/domain/repositories/concept_stock_repository.py
git commit -m "feat(data_engineering): add concept domain interfaces (gateway, repos, exceptions)"
```

---

## Task 3: 基础设施 — ORM 模型

**Files:**
- Create: `src/app/modules/data_engineering/infrastructure/models/concept_model.py`
- Create: `src/app/modules/data_engineering/infrastructure/models/concept_stock_model.py`

**Step 1: ConceptModel**
```python
# src/app/modules/data_engineering/infrastructure/models/concept_model.py
from datetime import datetime
from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.shared_kernel.infrastructure.database import Base

class ConceptModel(Base):
    """表 concept：概念板块基础信息。UNIQUE(source, third_code)。

    Attributes:
        id: 主键，自增。
        source: 数据来源（如 AKSHARE），存枚举值。
        third_code: 第三方概念代码（如 BK0818）。
        name: 概念名称。
        content_hash: SHA-256 前16位，用于增量同步变更检测。
        last_synced_at: 最后同步时间（UTC）。
        created_at: 创建时间（UTC）。
        updated_at: 最后更新时间（UTC）。
        version: 乐观锁版本号。
    """
    __tablename__ = "concept"
    __table_args__ = (UniqueConstraint("source", "third_code", name="uq_concept_source_third_code"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    third_code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(16), nullable=False)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
```

**Step 2: ConceptStockModel**
```python
# src/app/modules/data_engineering/infrastructure/models/concept_stock_model.py
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.shared_kernel.infrastructure.database import Base

class ConceptStockModel(Base):
    """表 concept_stock：概念-股票关联关系。UNIQUE(concept_id, source, stock_third_code)。

    Attributes:
        id: 主键，自增。
        concept_id: 关联 concept.id（级联删除）。
        source: 数据来源，存枚举值。
        stock_third_code: 股票第三方代码（如 000001）。
        stock_symbol: 匹配后的 StockBasic.symbol（如 000001.SZ）；匹配失败为 NULL。
        content_hash: SHA-256 前16位，用于增量同步变更检测。
        added_at: 关联添加时间（UTC）。
        created_at: 创建时间（UTC）。
        updated_at: 最后更新时间（UTC）。
        version: 乐观锁版本号。
    """
    __tablename__ = "concept_stock"
    __table_args__ = (
        UniqueConstraint("concept_id", "source", "stock_third_code", name="uq_concept_stock_concept_source_code"),
        Index("ix_concept_stock_symbol", "stock_symbol"),
        Index("ix_concept_stock_third_code", "stock_third_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    concept_id: Mapped[int] = mapped_column(ForeignKey("concept.id", ondelete="CASCADE"), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    stock_third_code: Mapped[str] = mapped_column(String(32), nullable=False)
    stock_symbol: Mapped[str | None] = mapped_column(String(32), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(16), nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
```

**Step 3: 验证**
```bash
python -c "
import app.modules.data_engineering.infrastructure.models.concept_model
import app.modules.data_engineering.infrastructure.models.concept_stock_model
print('ORM models OK')
"
```

**Step 4: Commit**
```bash
git add src/app/modules/data_engineering/infrastructure/models/concept_model.py \
        src/app/modules/data_engineering/infrastructure/models/concept_stock_model.py
git commit -m "feat(data_engineering): add ConceptModel and ConceptStockModel ORM models"
```

---

## Task 4: Alembic 数据库迁移

**Files:**
- Modify: `src/app/modules/data_engineering/infrastructure/models/__init__.py`（追加 import）
- Create: `migrations/versions/<timestamp>_add_concept_tables.py`（autogenerate 生成）

**Step 1: 确保模型被 Alembic 扫描**

在 `src/app/modules/data_engineering/infrastructure/models/__init__.py` 追加：
```python
from .concept_model import ConceptModel  # noqa: F401
from .concept_stock_model import ConceptStockModel  # noqa: F401
```

**Step 2: 生成迁移**
```bash
alembic revision --autogenerate -m "add_concept_tables"
```
Expected: 在 `migrations/versions/` 生成新文件，`upgrade()` 中包含 `create_table("concept", ...)` 和 `create_table("concept_stock", ...)`。

**Step 3: 核查生成文件**
- 确认 `concept_stock` 的 `concept_id` 外键有 `ondelete='CASCADE'`
- 确认两张表字段顺序与 ORM 模型一致

**Step 4: 应用迁移**
```bash
alembic upgrade head
```
Expected: `Running upgrade ... -> ..., add_concept_tables`

**Step 5: Commit**
```bash
git add migrations/versions/ src/app/modules/data_engineering/infrastructure/models/__init__.py
git commit -m "feat(data_engineering): add alembic migration for concept and concept_stock tables"
```

---

## Task 5: AkShareConceptMapper（单元测试）

**Files:**
- Create: `src/app/modules/data_engineering/infrastructure/gateways/mappers/akshare_concept_mapper.py`
- Create: `tests/unit/modules/data_engineering/infrastructure/gateways/mappers/test_akshare_concept_mapper.py`

**Step 1: 写失败测试**
```python
# tests/unit/modules/data_engineering/infrastructure/gateways/mappers/test_akshare_concept_mapper.py
from datetime import datetime, UTC
from hashlib import sha256
import pandas as pd
import pytest
from app.modules.data_engineering.domain.entities.concept import Concept
from app.modules.data_engineering.domain.exceptions import ExternalConceptServiceError
from app.modules.data_engineering.domain.value_objects.data_source import DataSource
from app.modules.data_engineering.infrastructure.gateways.mappers.akshare_concept_mapper import AkShareConceptMapper

NOW = datetime.now(UTC)

def _concept_df():
    return pd.DataFrame({"板块名称": ["融资融券", "人工智能"], "板块代码": ["BK0818", "BK0821"]})

def _stock_df():
    return pd.DataFrame({"代码": ["000001", "600000"], "名称": ["平安银行", "浦发银行"]})

class TestAkShareConceptMapper:
    def setup_method(self):
        self.m = AkShareConceptMapper()

    def test_rows_to_concepts_maps_fields(self) -> None:
        concepts = self.m.rows_to_concepts(_concept_df(), synced_at=NOW)
        assert len(concepts) == 2
        assert concepts[0].source == DataSource.AKSHARE
        assert concepts[0].third_code == "BK0818"
        assert concepts[0].name == "融资融券"
        assert concepts[0].id is None
        assert concepts[0].last_synced_at == NOW

    def test_rows_to_concepts_sets_content_hash(self) -> None:
        concepts = self.m.rows_to_concepts(_concept_df(), synced_at=NOW)
        expected = Concept.compute_hash(DataSource.AKSHARE, "BK0818", "融资融券")
        assert concepts[0].content_hash == expected

    def test_rows_to_concepts_raises_on_missing_column(self) -> None:
        with pytest.raises(ExternalConceptServiceError):
            self.m.rows_to_concepts(pd.DataFrame({"板块代码": ["BK0818"]}), synced_at=NOW)

    def test_rows_to_concepts_empty_df_returns_empty(self) -> None:
        df = pd.DataFrame({"板块名称": [], "板块代码": []})
        assert self.m.rows_to_concepts(df, synced_at=NOW) == []

    def test_rows_to_stock_tuples_maps_code_and_name(self) -> None:
        result = self.m.rows_to_stock_tuples(_stock_df())
        assert result == [("000001", "平安银行"), ("600000", "浦发银行")]

    def test_rows_to_stock_tuples_raises_on_missing_column(self) -> None:
        with pytest.raises(ExternalConceptServiceError):
            self.m.rows_to_stock_tuples(pd.DataFrame({"名称": ["平安银行"]}))
```

**Step 2: 运行确认失败**
```bash
pytest tests/unit/modules/data_engineering/infrastructure/gateways/mappers/test_akshare_concept_mapper.py -v
```
Expected: `ImportError: cannot import name 'AkShareConceptMapper'`

**Step 3: 实现 AkShareConceptMapper**
```python
# src/app/modules/data_engineering/infrastructure/gateways/mappers/akshare_concept_mapper.py
"""AKShare DataFrame → 领域实体映射。"""
from datetime import datetime
import pandas as pd
from app.modules.data_engineering.domain.entities.concept import Concept
from app.modules.data_engineering.domain.exceptions import ExternalConceptServiceError
from app.modules.data_engineering.domain.value_objects.data_source import DataSource


class AkShareConceptMapper:
    """AKShare API 响应（DataFrame）→ 领域实体；字段缺失或格式异常抛 ExternalConceptServiceError。"""

    def rows_to_concepts(self, df: pd.DataFrame, synced_at: datetime) -> list[Concept]:
        """概念板块 DataFrame → list[Concept]。"""
        try:
            result = []
            for _, row in df.iterrows():
                name = str(row["板块名称"]).strip()
                third_code = str(row["板块代码"]).strip()
                if not name or not third_code:
                    raise ExternalConceptServiceError(f"Empty name/code in row: {dict(row)}")
                result.append(Concept(
                    id=None,
                    source=DataSource.AKSHARE,
                    third_code=third_code,
                    name=name,
                    content_hash=Concept.compute_hash(DataSource.AKSHARE, third_code, name),
                    last_synced_at=synced_at,
                ))
            return result
        except KeyError as e:
            raise ExternalConceptServiceError(f"Missing required column: {e}") from e

    def rows_to_stock_tuples(self, df: pd.DataFrame) -> list[tuple[str, str]]:
        """成分股 DataFrame → [(stock_third_code, stock_name), ...]。"""
        try:
            return [(str(row["代码"]).strip(), str(row["名称"]).strip()) for _, row in df.iterrows()]
        except KeyError as e:
            raise ExternalConceptServiceError(f"Missing required column: {e}") from e
```

**Step 4: 运行确认通过**
```bash
pytest tests/unit/modules/data_engineering/infrastructure/gateways/mappers/test_akshare_concept_mapper.py -v
```
Expected: 6 tests PASSED

**Step 5: Commit**
```bash
git add src/app/modules/data_engineering/infrastructure/gateways/mappers/akshare_concept_mapper.py \
        tests/unit/modules/data_engineering/infrastructure/gateways/mappers/test_akshare_concept_mapper.py
git commit -m "feat(data_engineering): add AkShareConceptMapper with unit tests"
```

---

> **下一步:** 继续 `plan-part2.md`（Task 6-11：Gateway、Repository、Handler、API）
