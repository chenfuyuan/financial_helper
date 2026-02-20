# AKShare 概念板块同步 — 实现计划 Part 2a（Task 6-8）

> 接续自 `plan-part1.md`，后续见 `plan-part2b.md`（Task 9-11）

---

## Task 6: AkShareConceptGateway（单元测试）

**Files:**
- Create: `src/app/modules/data_engineering/infrastructure/gateways/akshare_concept_gateway.py`
- Create: `tests/unit/modules/data_engineering/infrastructure/gateways/test_akshare_concept_gateway.py`

**Step 1: 写失败测试**
```python
# tests/unit/modules/data_engineering/infrastructure/gateways/test_akshare_concept_gateway.py
from datetime import UTC, datetime
from unittest.mock import patch
import pandas as pd
import pytest
from app.modules.data_engineering.domain.exceptions import ExternalConceptServiceError
from app.modules.data_engineering.infrastructure.gateways.akshare_concept_gateway import AkShareConceptGateway

def _concept_df():
    return pd.DataFrame({"板块名称": ["融资融券"], "板块代码": ["BK0818"]})

def _stock_df():
    return pd.DataFrame({"代码": ["000001"], "名称": ["平安银行"]})

class TestAkShareConceptGateway:
    @pytest.mark.asyncio
    async def test_fetch_concepts_returns_list(self) -> None:
        gw = AkShareConceptGateway()
        with patch.object(gw, "_fetch_concepts_raw", return_value=_concept_df()):
            concepts = await gw.fetch_concepts()
        assert len(concepts) == 1
        assert concepts[0].third_code == "BK0818"

    @pytest.mark.asyncio
    async def test_fetch_concepts_wraps_exception(self) -> None:
        gw = AkShareConceptGateway()
        with patch.object(gw, "_fetch_concepts_raw", side_effect=Exception("network error")):
            with pytest.raises(ExternalConceptServiceError):
                await gw.fetch_concepts()

    @pytest.mark.asyncio
    async def test_fetch_concept_stocks_returns_tuples(self) -> None:
        gw = AkShareConceptGateway()
        with patch.object(gw, "_fetch_stocks_raw", return_value=_stock_df()):
            result = await gw.fetch_concept_stocks("BK0818", "融资融券")
        assert result == [("000001", "平安银行")]

    @pytest.mark.asyncio
    async def test_fetch_concept_stocks_wraps_exception(self) -> None:
        gw = AkShareConceptGateway()
        with patch.object(gw, "_fetch_stocks_raw", side_effect=Exception("timeout")):
            with pytest.raises(ExternalConceptServiceError):
                await gw.fetch_concept_stocks("BK0818", "融资融券")
```

**Step 2: 运行确认失败**
```bash
pytest tests/unit/modules/data_engineering/infrastructure/gateways/test_akshare_concept_gateway.py -v
```
Expected: `ImportError: cannot import name 'AkShareConceptGateway'`

**Step 3: 实现 AkShareConceptGateway**
```python
# src/app/modules/data_engineering/infrastructure/gateways/akshare_concept_gateway.py
"""AKShare 东方财富概念板块网关实现。"""
import asyncio
from datetime import UTC, datetime
import pandas as pd
from app.modules.data_engineering.domain.entities.concept import Concept
from app.modules.data_engineering.domain.exceptions import ExternalConceptServiceError
from app.modules.data_engineering.domain.gateways.concept_gateway import ConceptGateway
from .mappers.akshare_concept_mapper import AkShareConceptMapper


class AkShareConceptGateway(ConceptGateway):
    """调用 AKShare 东方财富接口拉取概念板块及成分股数据。"""

    def __init__(self, mapper: AkShareConceptMapper | None = None) -> None:
        self._mapper = mapper or AkShareConceptMapper()

    async def _fetch_concepts_raw(self) -> pd.DataFrame:
        """可被单测 patch。"""
        def _sync() -> pd.DataFrame:
            import akshare as ak  # type: ignore[import-untyped]
            return ak.stock_board_concept_name_em()
        return await asyncio.to_thread(_sync)

    async def _fetch_stocks_raw(self, concept_name: str) -> pd.DataFrame:
        """可被单测 patch。"""
        def _sync() -> pd.DataFrame:
            import akshare as ak  # type: ignore[import-untyped]
            return ak.stock_board_concept_cons_em(symbol=concept_name)
        return await asyncio.to_thread(_sync)

    async def fetch_concepts(self) -> list[Concept]:
        try:
            df = await self._fetch_concepts_raw()
            return self._mapper.rows_to_concepts(df, synced_at=datetime.now(UTC))
        except ExternalConceptServiceError:
            raise
        except Exception as e:
            raise ExternalConceptServiceError(f"AKShare fetch_concepts failed: {e}") from e

    async def fetch_concept_stocks(
        self, concept_third_code: str, concept_name: str
    ) -> list[tuple[str, str]]:
        try:
            df = await self._fetch_stocks_raw(concept_name)
            return self._mapper.rows_to_stock_tuples(df)
        except ExternalConceptServiceError:
            raise
        except Exception as e:
            raise ExternalConceptServiceError(
                f"AKShare fetch_concept_stocks failed ({concept_third_code}): {e}"
            ) from e
```

**Step 4: 运行确认通过**
```bash
pytest tests/unit/modules/data_engineering/infrastructure/gateways/test_akshare_concept_gateway.py -v
```
Expected: 4 tests PASSED

**Step 5: Commit**
```bash
git add src/app/modules/data_engineering/infrastructure/gateways/akshare_concept_gateway.py \
        tests/unit/modules/data_engineering/infrastructure/gateways/test_akshare_concept_gateway.py
git commit -m "feat(data_engineering): add AkShareConceptGateway with unit tests"
```

---

## Task 7: SqlAlchemyConceptRepository（集成测试）

**Files:**
- Create: `src/app/modules/data_engineering/infrastructure/repositories/sqlalchemy_concept_repository.py`
- Create: `tests/integration/modules/data_engineering/test_sqlalchemy_concept_repository.py`

**Step 1: 写失败测试**
```python
# tests/integration/modules/data_engineering/test_sqlalchemy_concept_repository.py
from datetime import UTC, datetime
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.modules.data_engineering.domain.entities.concept import Concept
from app.modules.data_engineering.domain.value_objects.data_source import DataSource
from app.modules.data_engineering.infrastructure.repositories.sqlalchemy_concept_repository import SqlAlchemyConceptRepository
from app.shared_kernel.infrastructure.database import Base

@pytest.fixture
async def sf():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await engine.dispose()

def _mk(third_code="BK0818", name="融资融券", cid=None):
    return Concept(id=cid, source=DataSource.AKSHARE, third_code=third_code, name=name,
                   content_hash=Concept.compute_hash(DataSource.AKSHARE, third_code, name),
                   last_synced_at=datetime.now(UTC))

class TestSqlAlchemyConceptRepository:
    async def test_save_new_assigns_id(self, sf) -> None:
        async with sf() as s:
            repo = SqlAlchemyConceptRepository(s)
            saved = await repo.save(_mk())
            await s.commit()
        assert saved.id is not None

    async def test_find_all_by_source(self, sf) -> None:
        async with sf() as s:
            repo = SqlAlchemyConceptRepository(s)
            await repo.save(_mk("BK0818")); await repo.save(_mk("BK0821", "人工智能"))
            await s.commit()
        async with sf() as s:
            concepts = await SqlAlchemyConceptRepository(s).find_all(DataSource.AKSHARE)
        assert len(concepts) == 2

    async def test_find_by_id_returns_none_for_missing(self, sf) -> None:
        async with sf() as s:
            assert await SqlAlchemyConceptRepository(s).find_by_id(99999) is None

    async def test_delete_removes_concept(self, sf) -> None:
        async with sf() as s:
            repo = SqlAlchemyConceptRepository(s)
            saved = await repo.save(_mk()); await s.commit()
        async with sf() as s:
            await SqlAlchemyConceptRepository(s).delete(saved.id); await s.commit()
        async with sf() as s:
            assert await SqlAlchemyConceptRepository(s).find_by_id(saved.id) is None

    async def test_save_existing_updates_name(self, sf) -> None:
        async with sf() as s:
            repo = SqlAlchemyConceptRepository(s)
            saved = await repo.save(_mk(name="旧名")); await s.commit()
        async with sf() as s:
            repo = SqlAlchemyConceptRepository(s)
            updated = _mk(name="新名"); updated.id = saved.id
            await repo.save(updated); await s.commit()
        async with sf() as s:
            result = await SqlAlchemyConceptRepository(s).find_by_id(saved.id)
        assert result.name == "新名"
```

**Step 2: 运行确认失败**
```bash
pytest tests/integration/modules/data_engineering/test_sqlalchemy_concept_repository.py -v
```

**Step 3: 实现 SqlAlchemyConceptRepository**
```python
# src/app/modules/data_engineering/infrastructure/repositories/sqlalchemy_concept_repository.py
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.data_engineering.domain.entities.concept import Concept
from app.modules.data_engineering.domain.repositories.concept_repository import ConceptRepository
from app.modules.data_engineering.domain.value_objects.data_source import DataSource
from app.shared_kernel.infrastructure.sqlalchemy_repository import SqlAlchemyRepository
from ..models.concept_model import ConceptModel


class SqlAlchemyConceptRepository(SqlAlchemyRepository[Concept, int | None], ConceptRepository):
    """概念板块仓储：save 返回含 DB 分配 id 的实体。"""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ConceptModel)

    def _to_entity(self, model: Any) -> Concept:
        return Concept(id=model.id, source=DataSource(model.source), third_code=model.third_code,
                       name=model.name, content_hash=model.content_hash, last_synced_at=model.last_synced_at)

    def _to_model(self, entity: Concept) -> Any:
        return ConceptModel(id=entity.id, source=entity.source.value, third_code=entity.third_code,
                            name=entity.name, content_hash=entity.content_hash, last_synced_at=entity.last_synced_at)

    async def find_all(self, source: DataSource) -> list[Concept]:
        result = await self._session.execute(select(ConceptModel).where(ConceptModel.source == source.value))
        return [self._to_entity(m) for m in result.scalars().all()]

    async def find_by_id(self, concept_id: int) -> Concept | None:
        m = await self._session.get(ConceptModel, concept_id)
        return self._to_entity(m) if m else None

    async def find_by_third_code(self, source: DataSource, third_code: str) -> Concept | None:
        stmt = select(ConceptModel).where(ConceptModel.source == source.value, ConceptModel.third_code == third_code)
        m = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._to_entity(m) if m else None

    async def save(self, concept: Concept) -> Concept:
        if concept.id is None:
            model = self._to_model(concept)
            self._session.add(model)
            await self._session.flush()
            return self._to_entity(model)
        model = await self._session.get(ConceptModel, concept.id)
        if model:
            model.name = concept.name
            model.content_hash = concept.content_hash
            model.last_synced_at = concept.last_synced_at
        return concept

    async def delete(self, concept_id: int) -> None:
        m = await self._session.get(ConceptModel, concept_id)
        if m:
            await self._session.delete(m)

    async def delete_many(self, concept_ids: list[int]) -> None:
        for cid in concept_ids:
            await self.delete(cid)
```

**Step 4: 运行确认通过**
```bash
pytest tests/integration/modules/data_engineering/test_sqlalchemy_concept_repository.py -v
```
Expected: 5 tests PASSED

**Step 5: Commit**
```bash
git add src/app/modules/data_engineering/infrastructure/repositories/sqlalchemy_concept_repository.py \
        tests/integration/modules/data_engineering/test_sqlalchemy_concept_repository.py
git commit -m "feat(data_engineering): add SqlAlchemyConceptRepository with integration tests"
```

---

## Task 8: SqlAlchemyConceptStockRepository（集成测试）

**Files:**
- Create: `src/app/modules/data_engineering/infrastructure/repositories/sqlalchemy_concept_stock_repository.py`
- Create: `tests/integration/modules/data_engineering/test_sqlalchemy_concept_stock_repository.py`

**Step 1: 写失败测试**
```python
# tests/integration/modules/data_engineering/test_sqlalchemy_concept_stock_repository.py
from datetime import UTC, datetime
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.modules.data_engineering.domain.entities.concept import Concept
from app.modules.data_engineering.domain.entities.concept_stock import ConceptStock
from app.modules.data_engineering.domain.value_objects.data_source import DataSource
from app.modules.data_engineering.infrastructure.repositories.sqlalchemy_concept_repository import SqlAlchemyConceptRepository
from app.modules.data_engineering.infrastructure.repositories.sqlalchemy_concept_stock_repository import SqlAlchemyConceptStockRepository
from app.shared_kernel.infrastructure.database import Base

@pytest.fixture
async def sf():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    await engine.dispose()

async def _mk_concept_id(sf) -> int:
    async with sf() as s:
        repo = SqlAlchemyConceptRepository(s)
        c = Concept(id=None, source=DataSource.AKSHARE, third_code="BK0818", name="融资融券",
                    content_hash="abc", last_synced_at=datetime.now(UTC))
        saved = await repo.save(c); await s.commit()
        return saved.id

def _mk_stock(concept_id, code="000001", symbol="000001.SZ"):
    return ConceptStock(id=None, concept_id=concept_id, source=DataSource.AKSHARE,
                        stock_third_code=code, stock_symbol=symbol,
                        content_hash=ConceptStock.compute_hash(DataSource.AKSHARE, code, symbol),
                        added_at=datetime.now(UTC))

class TestSqlAlchemyConceptStockRepository:
    async def test_save_many_and_find_by_concept_id(self, sf) -> None:
        cid = await _mk_concept_id(sf)
        async with sf() as s:
            repo = SqlAlchemyConceptStockRepository(s)
            await repo.save_many([_mk_stock(cid, "000001"), _mk_stock(cid, "600000", "600000.SH")])
            await s.commit()
        async with sf() as s:
            result = await SqlAlchemyConceptStockRepository(s).find_by_concept_id(cid)
        assert len(result) == 2

    async def test_delete_by_concept_id_removes_all(self, sf) -> None:
        cid = await _mk_concept_id(sf)
        async with sf() as s:
            repo = SqlAlchemyConceptStockRepository(s)
            await repo.save_many([_mk_stock(cid)]); await s.commit()
        async with sf() as s:
            await SqlAlchemyConceptStockRepository(s).delete_by_concept_id(cid); await s.commit()
        async with sf() as s:
            assert await SqlAlchemyConceptStockRepository(s).find_by_concept_id(cid) == []

    async def test_delete_many_removes_specified_ids(self, sf) -> None:
        cid = await _mk_concept_id(sf)
        async with sf() as s:
            repo = SqlAlchemyConceptStockRepository(s)
            await repo.save_many([_mk_stock(cid, "000001"), _mk_stock(cid, "600000", "600000.SH")])
            await s.commit()
        async with sf() as s:
            stocks = await SqlAlchemyConceptStockRepository(s).find_by_concept_id(cid)
        ids_to_delete = [stocks[0].id]
        async with sf() as s:
            await SqlAlchemyConceptStockRepository(s).delete_many(ids_to_delete); await s.commit()
        async with sf() as s:
            result = await SqlAlchemyConceptStockRepository(s).find_by_concept_id(cid)
        assert len(result) == 1
```

**Step 2: 运行确认失败**
```bash
pytest tests/integration/modules/data_engineering/test_sqlalchemy_concept_stock_repository.py -v
```

**Step 3: 实现 SqlAlchemyConceptStockRepository**
```python
# src/app/modules/data_engineering/infrastructure/repositories/sqlalchemy_concept_stock_repository.py
from typing import Any
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.data_engineering.domain.entities.concept_stock import ConceptStock
from app.modules.data_engineering.domain.repositories.concept_stock_repository import ConceptStockRepository
from app.modules.data_engineering.domain.value_objects.data_source import DataSource
from app.shared_kernel.infrastructure.sqlalchemy_repository import SqlAlchemyRepository
from ..models.concept_stock_model import ConceptStockModel


class SqlAlchemyConceptStockRepository(SqlAlchemyRepository[ConceptStock, int | None], ConceptStockRepository):

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ConceptStockModel)

    def _to_entity(self, model: Any) -> ConceptStock:
        return ConceptStock(id=model.id, concept_id=model.concept_id,
                            source=DataSource(model.source), stock_third_code=model.stock_third_code,
                            stock_symbol=model.stock_symbol, content_hash=model.content_hash,
                            added_at=model.added_at)

    def _to_model(self, entity: ConceptStock) -> Any:
        return ConceptStockModel(id=entity.id, concept_id=entity.concept_id,
                                 source=entity.source.value, stock_third_code=entity.stock_third_code,
                                 stock_symbol=entity.stock_symbol, content_hash=entity.content_hash,
                                 added_at=entity.added_at)

    async def find_by_concept_id(self, concept_id: int) -> list[ConceptStock]:
        result = await self._session.execute(
            select(ConceptStockModel).where(ConceptStockModel.concept_id == concept_id))
        return [self._to_entity(m) for m in result.scalars().all()]

    async def save_many(self, concept_stocks: list[ConceptStock]) -> None:
        for cs in concept_stocks:
            self._session.add(self._to_model(cs))
        await self._session.flush()

    async def delete_many(self, concept_stock_ids: list[int]) -> None:
        await self._session.execute(
            delete(ConceptStockModel).where(ConceptStockModel.id.in_(concept_stock_ids)))

    async def delete_by_concept_id(self, concept_id: int) -> None:
        await self._session.execute(
            delete(ConceptStockModel).where(ConceptStockModel.concept_id == concept_id))
```

**Step 4: 运行确认通过**
```bash
pytest tests/integration/modules/data_engineering/test_sqlalchemy_concept_stock_repository.py -v
```
Expected: 3 tests PASSED

**Step 5: Commit**
```bash
git add src/app/modules/data_engineering/infrastructure/repositories/sqlalchemy_concept_stock_repository.py \
        tests/integration/modules/data_engineering/test_sqlalchemy_concept_stock_repository.py
git commit -m "feat(data_engineering): add SqlAlchemyConceptStockRepository with integration tests"
```

---

> **下一步:** 继续 `plan-part2b.md`（Task 9-11：SyncConceptsHandler、Query Handlers、API 层）
