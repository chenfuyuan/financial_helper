# AKShare 概念板块同步 — 实现计划 Part 2b（Task 9-11）

> 接续自 `plan-part2a.md`

---

## Task 9: SyncConceptsHandler（单元测试）

**Files:**
- Create: `src/app/modules/data_engineering/application/commands/sync_concepts.py`
- Create: `src/app/modules/data_engineering/application/commands/sync_concepts_handler.py`
- Create: `tests/unit/modules/data_engineering/application/commands/test_sync_concepts_handler.py`

**Step 1: 写失败测试**
```python
# tests/unit/modules/data_engineering/application/commands/test_sync_concepts_handler.py
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
import pytest
from app.modules.data_engineering.application.commands.sync_concepts import SyncConcepts
from app.modules.data_engineering.application.commands.sync_concepts_handler import SyncConceptsHandler
from app.modules.data_engineering.domain.entities.concept import Concept
from app.modules.data_engineering.domain.exceptions import ExternalConceptServiceError
from app.modules.data_engineering.domain.value_objects.data_source import DataSource

def _mk(third_code="BK0818", name="融资融券", cid=None):
    return Concept(id=cid, source=DataSource.AKSHARE, third_code=third_code, name=name,
                   content_hash=Concept.compute_hash(DataSource.AKSHARE, third_code, name),
                   last_synced_at=datetime.now(UTC))

def _make_handler(remote, local=None):
    gateway = AsyncMock()
    gateway.fetch_concepts = AsyncMock(return_value=remote)
    gateway.fetch_concept_stocks = AsyncMock(return_value=[])
    saved = MagicMock(); saved.id = 1
    concept_repo = AsyncMock()
    concept_repo.find_all = AsyncMock(return_value=local or [])
    concept_repo.save = AsyncMock(return_value=saved)
    cs_repo = AsyncMock()
    cs_repo.find_by_concept_id = AsyncMock(return_value=[])
    sb_repo = AsyncMock()
    sb_repo.find_all = AsyncMock(return_value=[])
    uow = AsyncMock()
    h = SyncConceptsHandler(gateway=gateway, concept_repo=concept_repo,
                             concept_stock_repo=cs_repo, stock_basic_repo=sb_repo, uow=uow)
    h._uow = uow; h._gateway = gateway
    return h

class TestSyncConceptsHandler:
    @pytest.mark.asyncio
    async def test_new_concepts_persisted_and_commits(self) -> None:
        h = _make_handler(remote=[_mk()])
        result = await h.handle(SyncConcepts())
        assert result.new_concepts == 1
        h._uow.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_unchanged_concepts_not_counted_as_new(self) -> None:
        concept = _mk(cid=1)
        h = _make_handler(remote=[concept], local=[concept])
        result = await h.handle(SyncConcepts())
        assert result.new_concepts == 0 and result.modified_concepts == 0

    @pytest.mark.asyncio
    async def test_deleted_concepts_removed(self) -> None:
        h = _make_handler(remote=[], local=[_mk(cid=1)])
        result = await h.handle(SyncConcepts())
        assert result.deleted_concepts == 1

    @pytest.mark.asyncio
    async def test_gateway_error_no_commit(self) -> None:
        gateway = AsyncMock()
        gateway.fetch_concepts = AsyncMock(side_effect=ExternalConceptServiceError("fail"))
        uow = AsyncMock()
        h = SyncConceptsHandler(gateway=gateway, concept_repo=AsyncMock(),
                                  concept_stock_repo=AsyncMock(), stock_basic_repo=AsyncMock(), uow=uow)
        with pytest.raises(ExternalConceptServiceError):
            await h.handle(SyncConcepts())
        uow.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_modified_concept_triggers_stock_sync(self) -> None:
        local = _mk(cid=1, name="旧名称")
        remote = _mk(cid=None, name="新名称")
        h = _make_handler(remote=[remote], local=[local])
        result = await h.handle(SyncConcepts())
        assert result.modified_concepts == 1
        h._gateway.fetch_concept_stocks.assert_awaited()
```

**Step 2: 运行确认失败**
```bash
pytest tests/unit/modules/data_engineering/application/commands/test_sync_concepts_handler.py -v
```

**Step 3: 实现 SyncConcepts Command**
```python
# src/app/modules/data_engineering/application/commands/sync_concepts.py
from dataclasses import dataclass
from app.shared_kernel.application.command import Command

@dataclass(frozen=True)
class SyncConcepts(Command):
    """触发一次从 AKShare 拉取概念板块及成分股的同步。"""
    pass
```

**Step 4: 实现 SyncConceptsHandler**

> 📖 完整算法见 `design.md` Section "同步流程"。以下是核心骨架。

```python
# src/app/modules/data_engineering/application/commands/sync_concepts_handler.py
from dataclasses import dataclass
from datetime import UTC, datetime
from app.modules.data_engineering.domain.entities.concept_stock import ConceptStock
from app.modules.data_engineering.domain.gateways.concept_gateway import ConceptGateway
from app.modules.data_engineering.domain.repositories.concept_repository import ConceptRepository
from app.modules.data_engineering.domain.repositories.concept_stock_repository import ConceptStockRepository
from app.modules.data_engineering.domain.repositories.stock_basic_repository import StockBasicRepository
from app.modules.data_engineering.domain.value_objects.data_source import DataSource
from app.shared_kernel.application.command_handler import CommandHandler
from app.shared_kernel.domain.unit_of_work import UnitOfWork
from app.shared_kernel.infrastructure.logging import get_logger
from .sync_concepts import SyncConcepts

logger = get_logger(__name__)


@dataclass
class SyncConceptsResult:
    total_concepts: int = 0
    new_concepts: int = 0
    modified_concepts: int = 0
    deleted_concepts: int = 0
    total_stocks: int = 0
    new_stocks: int = 0
    modified_stocks: int = 0
    deleted_stocks: int = 0


def _infer_symbol(raw_code: str) -> str | None:
    """6→.SH, 0/3→.SZ, 4/8→.BJ，其余返回 None。"""
    if raw_code.startswith("6"): return f"{raw_code}.SH"
    if raw_code.startswith(("0", "3")): return f"{raw_code}.SZ"
    if raw_code.startswith(("4", "8")): return f"{raw_code}.BJ"
    return None


class SyncConceptsHandler(CommandHandler[SyncConcepts, SyncConceptsResult]):
    def __init__(self, gateway: ConceptGateway, concept_repo: ConceptRepository,
                 concept_stock_repo: ConceptStockRepository,
                 stock_basic_repo: StockBasicRepository, uow: UnitOfWork) -> None:
        self._gateway = gateway
        self._concept_repo = concept_repo
        self._concept_stock_repo = concept_stock_repo
        self._stock_basic_repo = stock_basic_repo
        self._uow = uow

    async def handle(self, command: SyncConcepts) -> SyncConceptsResult:
        result = SyncConceptsResult()
        now = datetime.now(UTC)
        remote_concepts = await self._gateway.fetch_concepts()
        result.total_concepts = len(remote_concepts)
        local_concepts = await self._concept_repo.find_all(DataSource.AKSHARE)
        local_map = {c.third_code: c for c in local_concepts}
        remote_map = {c.third_code: c for c in remote_concepts}
        # 预加载 StockBasic，避免 N+1
        all_stocks = await self._stock_basic_repo.find_all(DataSource.TUSHARE)
        symbol_map = {s.symbol: s for s in all_stocks}
        third_code_map = {s.third_code: s for s in all_stocks}
        # 删除
        deleted_keys = set(local_map) - set(remote_map)
        if deleted_keys:
            deleted_ids = [local_map[k].id for k in deleted_keys]
            for cid in deleted_ids:
                await self._concept_stock_repo.delete_by_concept_id(cid)
            await self._concept_repo.delete_many(deleted_ids)
            result.deleted_concepts = len(deleted_ids)
        # 新增/修改/未变更
        for third_code, remote_concept in remote_map.items():
            local_concept = local_map.get(third_code)
            if local_concept is None:
                saved = await self._concept_repo.save(remote_concept)
                stocks = await self._gateway.fetch_concept_stocks(third_code, remote_concept.name)
                new_cs = self._build_stocks(saved.id, stocks, symbol_map, third_code_map, now)
                if new_cs: await self._concept_stock_repo.save_many(new_cs)
                result.new_concepts += 1; result.new_stocks += len(new_cs)
            elif local_concept.content_hash != remote_concept.content_hash:
                remote_concept.id = local_concept.id
                await self._concept_repo.save(remote_concept)
                na, nm, nd = await self._sync_stocks(
                    local_concept.id, third_code, remote_concept.name,
                    symbol_map, third_code_map, now)
                result.modified_concepts += 1
                result.new_stocks += na; result.modified_stocks += nm; result.deleted_stocks += nd
            else:
                local_concept.last_synced_at = now
                await self._concept_repo.save(local_concept)
        await self._uow.commit()
        logger.info("Sync done: %s", result)
        return result

    def _build_stocks(self, concept_id, raw_stocks, symbol_map, third_code_map, now):
        result = []
        for code, _ in raw_stocks:
            candidate = _infer_symbol(code)
            matched = None
            if candidate:
                matched = symbol_map.get(candidate, third_code_map.get(candidate))
                matched = matched.symbol if matched else None
            if matched is None:
                logger.warning("Cannot match stock_code=%s to StockBasic", code)
            result.append(ConceptStock(
                id=None, concept_id=concept_id, source=DataSource.AKSHARE,
                stock_third_code=code, stock_symbol=matched,
                content_hash=ConceptStock.compute_hash(DataSource.AKSHARE, code, matched),
                added_at=now,
            ))
        return result

    async def _sync_stocks(self, concept_id, third_code, concept_name, symbol_map, third_code_map, now):
        raw = await self._gateway.fetch_concept_stocks(third_code, concept_name)
        remote_cs = self._build_stocks(concept_id, raw, symbol_map, third_code_map, now)
        local_cs = await self._concept_stock_repo.find_by_concept_id(concept_id)
        lm = {cs.stock_third_code: cs for cs in local_cs}
        rm = {cs.stock_third_code: cs for cs in remote_cs}
        to_del = [lm[k].id for k in set(lm) - set(rm)]
        to_add = [rm[k] for k in set(rm) - set(lm)]
        to_upd = [rm[k] for k in set(rm) & set(lm) if rm[k].content_hash != lm[k].content_hash]
        if to_del: await self._concept_stock_repo.delete_many(to_del)
        if to_add: await self._concept_stock_repo.save_many(to_add)
        if to_upd:
            for cs in to_upd: cs.id = lm[cs.stock_third_code].id
            await self._concept_stock_repo.save_many(to_upd)
        return len(to_add), len(to_upd), len(to_del)
```

**Step 5: 运行确认通过**
```bash
pytest tests/unit/modules/data_engineering/application/commands/test_sync_concepts_handler.py -v
```
Expected: 5 tests PASSED

**Step 6: Commit**
```bash
git add src/app/modules/data_engineering/application/commands/sync_concepts.py \
        src/app/modules/data_engineering/application/commands/sync_concepts_handler.py \
        tests/unit/modules/data_engineering/application/commands/test_sync_concepts_handler.py
git commit -m "feat(data_engineering): add SyncConceptsHandler with two-level incremental sync"
```

---

## Task 10: GetConceptsHandler + GetConceptStocksHandler（单元测试）

**Files:**
- Create: `src/app/modules/data_engineering/application/queries/get_concepts.py`
- Create: `src/app/modules/data_engineering/application/queries/get_concepts_handler.py`
- Create: `src/app/modules/data_engineering/application/queries/get_concept_stocks.py`
- Create: `src/app/modules/data_engineering/application/queries/get_concept_stocks_handler.py`
- Create: `tests/unit/modules/data_engineering/application/queries/test_concept_query_handlers.py`

**Step 1: 写失败测试**
```python
# tests/unit/modules/data_engineering/application/queries/test_concept_query_handlers.py
from datetime import UTC, datetime
from unittest.mock import AsyncMock
import pytest
from app.modules.data_engineering.application.queries.get_concepts import GetConcepts
from app.modules.data_engineering.application.queries.get_concepts_handler import GetConceptsHandler
from app.modules.data_engineering.application.queries.get_concept_stocks import GetConceptStocks
from app.modules.data_engineering.application.queries.get_concept_stocks_handler import GetConceptStocksHandler
from app.modules.data_engineering.domain.entities.concept import Concept
from app.modules.data_engineering.domain.entities.concept_stock import ConceptStock
from app.modules.data_engineering.domain.exceptions import ConceptNotFoundError
from app.modules.data_engineering.domain.value_objects.data_source import DataSource

def _mk_c(cid=1):
    return Concept(id=cid, source=DataSource.AKSHARE, third_code="BK0818", name="融资融券",
                   content_hash="abc", last_synced_at=datetime.now(UTC))

def _mk_s():
    return ConceptStock(id=1, concept_id=1, source=DataSource.AKSHARE, stock_third_code="000001",
                        stock_symbol="000001.SZ", content_hash="def", added_at=datetime.now(UTC))

class TestGetConceptsHandler:
    @pytest.mark.asyncio
    async def test_returns_all_for_source(self) -> None:
        repo = AsyncMock(); repo.find_all = AsyncMock(return_value=[_mk_c(), _mk_c(2)])
        result = await GetConceptsHandler(concept_repo=repo).handle(GetConcepts(source=DataSource.AKSHARE))
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_none(self) -> None:
        repo = AsyncMock(); repo.find_all = AsyncMock(return_value=[])
        result = await GetConceptsHandler(concept_repo=repo).handle(GetConcepts(source=DataSource.AKSHARE))
        assert result == []

class TestGetConceptStocksHandler:
    @pytest.mark.asyncio
    async def test_returns_stocks_for_existing_concept(self) -> None:
        cr = AsyncMock(); cr.find_by_id = AsyncMock(return_value=_mk_c())
        csr = AsyncMock(); csr.find_by_concept_id = AsyncMock(return_value=[_mk_s()])
        result = await GetConceptStocksHandler(concept_repo=cr, concept_stock_repo=csr).handle(GetConceptStocks(concept_id=1))
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_raises_concept_not_found(self) -> None:
        cr = AsyncMock(); cr.find_by_id = AsyncMock(return_value=None)
        with pytest.raises(ConceptNotFoundError):
            await GetConceptStocksHandler(concept_repo=cr, concept_stock_repo=AsyncMock()).handle(GetConceptStocks(concept_id=99))
```

**Step 2: 运行确认失败**
```bash
pytest tests/unit/modules/data_engineering/application/queries/test_concept_query_handlers.py -v
```

**Step 3: 实现 Queries 和 Handlers**
```python
# get_concepts.py
from dataclasses import dataclass
from app.modules.data_engineering.domain.value_objects.data_source import DataSource
from app.shared_kernel.application.query import Query

@dataclass(frozen=True)
class GetConcepts(Query):
    source: DataSource | None = None
```

```python
# get_concepts_handler.py
from app.modules.data_engineering.domain.entities.concept import Concept
from app.modules.data_engineering.domain.repositories.concept_repository import ConceptRepository
from app.modules.data_engineering.domain.value_objects.data_source import DataSource
from app.shared_kernel.application.query_handler import QueryHandler
from .get_concepts import GetConcepts

class GetConceptsHandler(QueryHandler[GetConcepts, list[Concept]]):
    def __init__(self, concept_repo: ConceptRepository) -> None:
        self._concept_repo = concept_repo

    async def handle(self, query: GetConcepts) -> list[Concept]:
        return await self._concept_repo.find_all(query.source or DataSource.AKSHARE)
```

```python
# get_concept_stocks.py
from dataclasses import dataclass
from app.shared_kernel.application.query import Query

@dataclass(frozen=True)
class GetConceptStocks(Query):
    concept_id: int
```

```python
# get_concept_stocks_handler.py
from app.modules.data_engineering.domain.entities.concept_stock import ConceptStock
from app.modules.data_engineering.domain.exceptions import ConceptNotFoundError
from app.modules.data_engineering.domain.repositories.concept_repository import ConceptRepository
from app.modules.data_engineering.domain.repositories.concept_stock_repository import ConceptStockRepository
from app.shared_kernel.application.query_handler import QueryHandler
from .get_concept_stocks import GetConceptStocks

class GetConceptStocksHandler(QueryHandler[GetConceptStocks, list[ConceptStock]]):
    def __init__(self, concept_repo: ConceptRepository, concept_stock_repo: ConceptStockRepository) -> None:
        self._concept_repo = concept_repo; self._concept_stock_repo = concept_stock_repo

    async def handle(self, query: GetConceptStocks) -> list[ConceptStock]:
        if not await self._concept_repo.find_by_id(query.concept_id):
            raise ConceptNotFoundError(f"Concept {query.concept_id} not found")
        return await self._concept_stock_repo.find_by_concept_id(query.concept_id)
```

**Step 4: 运行确认通过**
```bash
pytest tests/unit/modules/data_engineering/application/queries/test_concept_query_handlers.py -v
```
Expected: 4 tests PASSED

**Step 5: Commit**
```bash
git add src/app/modules/data_engineering/application/queries/ \
        tests/unit/modules/data_engineering/application/queries/
git commit -m "feat(data_engineering): add GetConceptsHandler and GetConceptStocksHandler"
```

---

## Task 11: 接口层 — Router、Dependencies、注册、API 测试

**Files:**
- Create: `src/app/modules/data_engineering/interfaces/api/concept_router.py`
- Modify: `src/app/modules/data_engineering/interfaces/dependencies.py`（追加三个 factory 函数）
- Modify: `src/app/interfaces/module_registry.py`（注册 concept_router）
- Create: `tests/api/modules/data_engineering/test_concept_router.py`

**Step 1: 写失败测试**
```python
# tests/api/modules/data_engineering/test_concept_router.py
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
import pytest
from app.modules.data_engineering.domain.entities.concept import Concept
from app.modules.data_engineering.domain.value_objects.data_source import DataSource

def _mk(cid=None):
    return Concept(id=cid, source=DataSource.AKSHARE, third_code="BK0818",
                   name="融资融券", content_hash="abc", last_synced_at=datetime.now(UTC))

class TestConceptRouter:
    @pytest.mark.asyncio
    async def test_post_sync_returns_200_with_counts(self, api_client) -> None:
        with patch("app.modules.data_engineering.interfaces.dependencies.AkShareConceptGateway") as M:
            M.return_value.fetch_concepts = AsyncMock(return_value=[_mk()])
            M.return_value.fetch_concept_stocks = AsyncMock(return_value=[])
            response = await api_client.post("/api/v1/data-engineering/concepts/sync")
        assert response.status_code == 200
        body = response.json()
        assert body["code"] == 200
        assert "new_concepts" in body["data"]

    @pytest.mark.asyncio
    async def test_get_concepts_returns_200_empty_list(self, api_client) -> None:
        response = await api_client.get("/api/v1/data-engineering/concepts")
        assert response.status_code == 200
        assert response.json()["data"] == []

    @pytest.mark.asyncio
    async def test_get_concept_stocks_not_found_returns_404(self, api_client) -> None:
        response = await api_client.get("/api/v1/data-engineering/concepts/99999/stocks")
        assert response.status_code == 404
```

**Step 2: 运行确认失败**
```bash
pytest tests/api/modules/data_engineering/test_concept_router.py -v
```

**Step 3: 实现 concept_router**
```python
# src/app/modules/data_engineering/interfaces/api/concept_router.py
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.interfaces.response import ApiResponse
from app.modules.data_engineering.domain.exceptions import ConceptNotFoundError
from app.modules.data_engineering.domain.value_objects.data_source import DataSource
from ..dependencies import get_get_concept_stocks_handler, get_get_concepts_handler, get_sync_concepts_handler

router = APIRouter(prefix="/concepts", tags=["concepts"])

class SyncConceptsResponse(BaseModel):
    total_concepts: int; new_concepts: int; modified_concepts: int; deleted_concepts: int
    total_stocks: int; new_stocks: int; modified_stocks: int; deleted_stocks: int

class ConceptResponse(BaseModel):
    id: int; source: str; third_code: str; name: str; last_synced_at: datetime

class ConceptStockResponse(BaseModel):
    id: int; concept_id: int; source: str; stock_third_code: str
    stock_symbol: str | None; added_at: datetime

@router.post("/sync", response_model=ApiResponse[SyncConceptsResponse])
async def sync_concepts(handler=Depends(get_sync_concepts_handler)):
    from app.modules.data_engineering.application.commands.sync_concepts import SyncConcepts
    result = await handler.handle(SyncConcepts())
    return ApiResponse.success(SyncConceptsResponse(**result.__dict__))

@router.get("", response_model=ApiResponse[list[ConceptResponse]])
async def get_concepts(source: DataSource | None = None, handler=Depends(get_get_concepts_handler)):
    from app.modules.data_engineering.application.queries.get_concepts import GetConcepts
    concepts = await handler.handle(GetConcepts(source=source))
    return ApiResponse.success([ConceptResponse(id=c.id, source=c.source.value,
        third_code=c.third_code, name=c.name, last_synced_at=c.last_synced_at) for c in concepts])

@router.get("/{concept_id}/stocks", response_model=ApiResponse[list[ConceptStockResponse]])
async def get_concept_stocks(concept_id: int, handler=Depends(get_get_concept_stocks_handler)):
    from app.modules.data_engineering.application.queries.get_concept_stocks import GetConceptStocks
    try:
        stocks = await handler.handle(GetConceptStocks(concept_id=concept_id))
    except ConceptNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return ApiResponse.success([ConceptStockResponse(id=s.id, concept_id=s.concept_id,
        source=s.source.value, stock_third_code=s.stock_third_code,
        stock_symbol=s.stock_symbol, added_at=s.added_at) for s in stocks])
```

**Step 4: 在 dependencies.py 追加三个 Factory 函数**
```python
# 追加到 src/app/modules/data_engineering/interfaces/dependencies.py
def get_sync_concepts_handler(uow: SqlAlchemyUnitOfWork = Depends(get_uow)) -> SyncConceptsHandler:
    from app.modules.data_engineering.infrastructure.gateways.akshare_concept_gateway import AkShareConceptGateway
    from app.modules.data_engineering.infrastructure.repositories.sqlalchemy_concept_repository import SqlAlchemyConceptRepository
    from app.modules.data_engineering.infrastructure.repositories.sqlalchemy_concept_stock_repository import SqlAlchemyConceptStockRepository
    from app.modules.data_engineering.application.commands.sync_concepts_handler import SyncConceptsHandler
    return SyncConceptsHandler(
        gateway=AkShareConceptGateway(),
        concept_repo=SqlAlchemyConceptRepository(uow.session),
        concept_stock_repo=SqlAlchemyConceptStockRepository(uow.session),
        stock_basic_repo=SqlAlchemyStockBasicRepository(uow.session),
        uow=uow,
    )

def get_get_concepts_handler(uow: SqlAlchemyUnitOfWork = Depends(get_uow)) -> GetConceptsHandler:
    from app.modules.data_engineering.infrastructure.repositories.sqlalchemy_concept_repository import SqlAlchemyConceptRepository
    from app.modules.data_engineering.application.queries.get_concepts_handler import GetConceptsHandler
    return GetConceptsHandler(concept_repo=SqlAlchemyConceptRepository(uow.session))

def get_get_concept_stocks_handler(uow: SqlAlchemyUnitOfWork = Depends(get_uow)) -> GetConceptStocksHandler:
    from app.modules.data_engineering.infrastructure.repositories.sqlalchemy_concept_repository import SqlAlchemyConceptRepository
    from app.modules.data_engineering.infrastructure.repositories.sqlalchemy_concept_stock_repository import SqlAlchemyConceptStockRepository
    from app.modules.data_engineering.application.queries.get_concept_stocks_handler import GetConceptStocksHandler
    return GetConceptStocksHandler(
        concept_repo=SqlAlchemyConceptRepository(uow.session),
        concept_stock_repo=SqlAlchemyConceptStockRepository(uow.session),
    )
```

**Step 5: 在 module_registry.py 注册路由**

在 `src/app/interfaces/module_registry.py` 的 `_collect_module_routers()` 函数中追加：
```python
from app.modules.data_engineering.interfaces.api.concept_router import router as concept_router
routers.append(concept_router)
```
同时在 `tests/api/conftest.py` 的 `api_client` fixture 中追加 concept 模型的 import：
```python
import app.modules.data_engineering.infrastructure.models.concept_model  # noqa: F401
import app.modules.data_engineering.infrastructure.models.concept_stock_model  # noqa: F401
```

**Step 6: 运行所有测试确认通过**
```bash
pytest tests/api/modules/data_engineering/test_concept_router.py -v
pytest tests/ -v --tb=short  # 全量回归
```
Expected: 所有新增测试 PASSED，无回归。

**Step 7: Commit**
```bash
git add src/app/modules/data_engineering/interfaces/api/concept_router.py \
        src/app/modules/data_engineering/interfaces/dependencies.py \
        src/app/interfaces/module_registry.py \
        tests/api/modules/data_engineering/test_concept_router.py
git commit -m "feat(data_engineering): add concept router, dependencies, and API tests"
```

---

## 全量验证

```bash
# 所有测试
pytest tests/ -v --tb=short

# 架构守卫
python -m pytest tests/architecture/ -v

# 全量回归
pytest --cov=app --cov-report=term-missing
```
