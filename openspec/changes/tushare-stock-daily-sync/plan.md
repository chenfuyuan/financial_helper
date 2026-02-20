# Tushare Stock Daily Sync Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement stock daily data synchronization from TuShare, including historical (with breakpoint resume) and incremental sync, with robust error handling and token bucket rate limiting.

**Architecture:** DDD + Clean Architecture. `StockDailyGateway` encapsulates 3 TuShare APIs with token bucket rate limiting. `StockDailyRepository` provides upsert and breakpoint resume. Application layer orchestrates sync and retry logic.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy (asyncpg), PostgreSQL, TuShare, pytest.

---

## 1. Database Migration

### Task 1.1: Create Alembic Migration

**Files:**
- Create: `migrations/versions/YYYYMMDD_HHMM_add_stock_daily_tables.py` (generate via `alembic revision`)

**Step 1: Write the migration script**
Add `stock_daily` and `stock_daily_sync_failure` tables.

**Step 2: Run migration**
Run: `alembic upgrade head`
Expected: Tables created successfully in database.

**Step 3: Commit**
```bash
git add migrations/
git commit -m "chore: add stock_daily and sync_failure tables"
```

---

## 2. Domain Layer

### Task 2.1: Implement Domain Entities

**Files:**
- Create: `src/app/modules/data_engineering/domain/entities/stock_daily.py`
- Create: `src/app/modules/data_engineering/domain/entities/stock_daily_sync_failure.py`
- Test: `tests/unit/modules/data_engineering/domain/entities/test_stock_daily.py`

**Step 1: Write failing test**
Create test verifying entity instantiation and attribute assignment (pure dataclass tests).

**Step 2: Run test to verify it fails**
Run: `pytest tests/unit/modules/data_engineering/domain/entities/test_stock_daily.py -v`
Expected: FAIL (module not found)

**Step 3: Write minimal implementation**
Implement `StockDaily` and `StockDailySyncFailure` dataclasses.

**Step 4: Run test to verify it passes**
Run: `pytest tests/unit/modules/data_engineering/domain/entities/test_stock_daily.py -v`
Expected: PASS

**Step 5: Commit**
```bash
git add src/app/modules/data_engineering/domain/entities/ tests/unit/modules/data_engineering/domain/entities/
git commit -m "feat(data_engineering): add StockDaily and StockDailySyncFailure entities"
```

### Task 2.2: Implement Interfaces (Gateway & Repository)

**Files:**
- Create: `src/app/modules/data_engineering/domain/gateways/stock_daily_gateway.py`
- Create: `src/app/modules/data_engineering/domain/repositories/stock_daily_repository.py`
- Create: `src/app/modules/data_engineering/domain/repositories/stock_daily_sync_failure_repository.py`

**Step 1: Write implementation**
Define ABCs for the gateway and two repositories.

**Step 2: Commit**
```bash
git add src/app/modules/data_engineering/domain/gateways/ src/app/modules/data_engineering/domain/repositories/
git commit -m "feat(data_engineering): add gateway and repository interfaces for stock daily"
```

---

## 3. Infrastructure Layer (Models & Mappers)

### Task 3.1: Implement SQLAlchemy Models

**Files:**
- Create: `src/app/modules/data_engineering/infrastructure/models/stock_daily_model.py`
- Create: `src/app/modules/data_engineering/infrastructure/models/stock_daily_sync_failure_model.py`
- Modify: `src/app/modules/data_engineering/infrastructure/models/__init__.py`

**Step 1: Write implementation**
Define SQLAlchemy models matching the migration.

**Step 2: Commit**
```bash
git add src/app/modules/data_engineering/infrastructure/models/
git commit -m "feat(data_engineering): add sqlalchemy models for stock daily"
```

### Task 3.2: Implement Persistence Mappers

**Files:**
- Create: `src/app/modules/data_engineering/infrastructure/repositories/mappers/stock_daily_persistence_mapper.py`
- Create: `src/app/modules/data_engineering/infrastructure/repositories/mappers/stock_daily_sync_failure_persistence_mapper.py`
- Test: `tests/unit/modules/data_engineering/infrastructure/repositories/mappers/test_stock_daily_persistence_mapper.py`

**Step 1: Write failing test**
Create test verifying entity to dict mapping.

**Step 2: Run test to verify it fails**
Run: `pytest tests/unit/modules/data_engineering/infrastructure/repositories/mappers/test_stock_daily_persistence_mapper.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**
Implement mapper classes to convert entities to dictionaries for upsert.

**Step 4: Run test to verify it passes**
Run: `pytest tests/unit/modules/data_engineering/infrastructure/repositories/mappers/test_stock_daily_persistence_mapper.py -v`
Expected: PASS

**Step 5: Commit**
```bash
git add src/app/modules/data_engineering/infrastructure/repositories/mappers/ tests/unit/modules/data_engineering/infrastructure/repositories/mappers/
git commit -m "feat(data_engineering): add persistence mappers for stock daily"
```

---

## 4. Infrastructure Layer (Gateway)

### Task 4.1: Implement Token Bucket Rate Limiter

**Files:**
- Create: `src/app/shared_kernel/infrastructure/rate_limiter.py`
- Test: `tests/unit/shared_kernel/infrastructure/test_rate_limiter.py`

**Step 1: Write failing test**
Create test for async token bucket (acquire, refill).

**Step 2: Run test to verify it fails**
Run: `pytest tests/unit/shared_kernel/infrastructure/test_rate_limiter.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**
Implement `AsyncTokenBucket` with capacity and refill rate.

**Step 4: Run test to verify it passes**
Run: `pytest tests/unit/shared_kernel/infrastructure/test_rate_limiter.py -v`
Expected: PASS

**Step 5: Commit**
```bash
git add src/app/shared_kernel/infrastructure/rate_limiter.py tests/unit/shared_kernel/infrastructure/test_rate_limiter.py
git commit -m "feat(shared_kernel): add AsyncTokenBucket rate limiter"
```

### Task 4.2: Implement TuShare Gateway Mapper

**Files:**
- Create: `src/app/modules/data_engineering/infrastructure/gateways/mappers/tushare_stock_daily_mapper.py`
- Test: `tests/unit/modules/data_engineering/infrastructure/gateways/mappers/test_tushare_stock_daily_mapper.py`

**Step 1: Write failing test**
Test mapping of combined TuShare dicts (daily, adj_factor, daily_basic) to `StockDaily`, including handling `None` for daily_basic fields.

**Step 2: Run test to verify it fails**
Run: `pytest tests/unit/modules/data_engineering/infrastructure/gateways/mappers/test_tushare_stock_daily_mapper.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**
Implement mapper handling data conversion and nullability.

**Step 4: Run test to verify it passes**
Run: `pytest tests/unit/modules/data_engineering/infrastructure/gateways/mappers/test_tushare_stock_daily_mapper.py -v`
Expected: PASS

**Step 5: Commit**
```bash
git add src/app/modules/data_engineering/infrastructure/gateways/mappers/tushare_stock_daily_mapper.py tests/unit/modules/data_engineering/infrastructure/gateways/mappers/test_tushare_stock_daily_mapper.py
git commit -m "feat(data_engineering): add tushare gateway mapper for stock daily"
```

### Task 4.3: Implement TuShare Gateway

**Files:**
- Create: `src/app/modules/data_engineering/infrastructure/gateways/tushare_stock_daily_gateway.py`
- Test: `tests/integration/modules/data_engineering/infrastructure/gateways/test_tushare_stock_daily_gateway.py` (Mock TuShare)

**Step 1: Write failing test**
Test `fetch_stock_daily` and `fetch_daily_all_by_date` with mocked TuShare client, verifying 3 API calls and pagination.

**Step 2: Run test to verify it fails**
Run: `pytest tests/integration/modules/data_engineering/infrastructure/gateways/test_tushare_stock_daily_gateway.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**
Implement gateway using TokenBucket, coordinating daily, adj_factor, and daily_basic calls.

**Step 4: Run test to verify it passes**
Run: `pytest tests/integration/modules/data_engineering/infrastructure/gateways/test_tushare_stock_daily_gateway.py -v`
Expected: PASS

**Step 5: Commit**
```bash
git add src/app/modules/data_engineering/infrastructure/gateways/tushare_stock_daily_gateway.py tests/integration/modules/data_engineering/infrastructure/gateways/test_tushare_stock_daily_gateway.py
git commit -m "feat(data_engineering): add TuShareStockDailyGateway"
```

---

## 5. Infrastructure Layer (Repositories)

### Task 5.1: Implement StockDailyRepository

**Files:**
- Create: `src/app/modules/data_engineering/infrastructure/repositories/sqlalchemy_stock_daily_repository.py`
- Test: `tests/integration/modules/data_engineering/infrastructure/repositories/test_sqlalchemy_stock_daily_repository.py`

**Step 1: Write failing test**
Test `upsert_many` (insert and update) and `get_latest_trade_date` with test DB.

**Step 2: Run test to verify it fails**
Run: `pytest tests/integration/modules/data_engineering/infrastructure/repositories/test_sqlalchemy_stock_daily_repository.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**
Implement `SqlAlchemyStockDailyRepository` with `ON CONFLICT DO UPDATE`.

**Step 4: Run test to verify it passes**
Run: `pytest tests/integration/modules/data_engineering/infrastructure/repositories/test_sqlalchemy_stock_daily_repository.py -v`
Expected: PASS

**Step 5: Commit**
```bash
git add src/app/modules/data_engineering/infrastructure/repositories/sqlalchemy_stock_daily_repository.py tests/integration/modules/data_engineering/infrastructure/repositories/test_sqlalchemy_stock_daily_repository.py
git commit -m "feat(data_engineering): add SqlAlchemyStockDailyRepository"
```

### Task 5.2: Implement SyncFailureRepository

**Files:**
- Create: `src/app/modules/data_engineering/infrastructure/repositories/sqlalchemy_stock_daily_sync_failure_repository.py`
- Test: `tests/integration/modules/data_engineering/infrastructure/repositories/test_sqlalchemy_stock_daily_sync_failure_repository.py`

**Step 1: Write failing test**
Test `save`, `find_unresolved`, and `mark_resolved`.

**Step 2: Run test to verify it fails**
Run: `pytest tests/integration/modules/data_engineering/infrastructure/repositories/test_sqlalchemy_stock_daily_sync_failure_repository.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**
Implement `SqlAlchemyStockDailySyncFailureRepository`.

**Step 4: Run test to verify it passes**
Run: `pytest tests/integration/modules/data_engineering/infrastructure/repositories/test_sqlalchemy_stock_daily_sync_failure_repository.py -v`
Expected: PASS

**Step 5: Commit**
```bash
git add src/app/modules/data_engineering/infrastructure/repositories/sqlalchemy_stock_daily_sync_failure_repository.py tests/integration/modules/data_engineering/infrastructure/repositories/test_sqlalchemy_stock_daily_sync_failure_repository.py
git commit -m "feat(data_engineering): add SqlAlchemyStockDailySyncFailureRepository"
```

---

## 6. Application Layer

### Task 6.1: Implement Sync Increment Command & Handler

**Files:**
- Create: `src/app/modules/data_engineering/application/commands/sync_stock_daily_increment.py`
- Create: `src/app/modules/data_engineering/application/commands/sync_stock_daily_increment_handler.py`
- Test: `tests/unit/modules/data_engineering/application/commands/test_sync_stock_daily_increment_handler.py`

**Step 1: Write failing test**
Test incremental sync with mocked Gateway, Repository, and UoW.

**Step 2: Run test to verify it fails**
Run: `pytest tests/unit/modules/data_engineering/application/commands/test_sync_stock_daily_increment_handler.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**
Implement Command and Handler logic (default date, fetch all, upsert, commit).

**Step 4: Run test to verify it passes**
Run: `pytest tests/unit/modules/data_engineering/application/commands/test_sync_stock_daily_increment_handler.py -v`
Expected: PASS

**Step 5: Commit**
```bash
git add src/app/modules/data_engineering/application/commands/sync_stock_daily_increment*.py tests/unit/modules/data_engineering/application/commands/test_sync_stock_daily_increment_handler.py
git commit -m "feat(data_engineering): add incremental sync command and handler"
```

### Task 6.2: Implement Sync History Command & Handler

**Files:**
- Create: `src/app/modules/data_engineering/application/commands/sync_stock_daily_history.py`
- Create: `src/app/modules/data_engineering/application/commands/sync_stock_daily_history_handler.py`
- Test: `tests/unit/modules/data_engineering/application/commands/test_sync_stock_daily_history_handler.py`

**Step 1: Write failing test**
Test history sync (resume, skip if up-to-date, independent transaction, failure recording) with mocked deps.

**Step 2: Run test to verify it fails**
Run: `pytest tests/unit/modules/data_engineering/application/commands/test_sync_stock_daily_history_handler.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**
Implement Command and Handler logic.

**Step 4: Run test to verify it passes**
Run: `pytest tests/unit/modules/data_engineering/application/commands/test_sync_stock_daily_history_handler.py -v`
Expected: PASS

**Step 5: Commit**
```bash
git add src/app/modules/data_engineering/application/commands/sync_stock_daily_history*.py tests/unit/modules/data_engineering/application/commands/test_sync_stock_daily_history_handler.py
git commit -m "feat(data_engineering): add history sync command and handler"
```

### Task 6.3: Implement Retry Failures Command & Handler

**Files:**
- Create: `src/app/modules/data_engineering/application/commands/retry_stock_daily_sync_failures.py`
- Create: `src/app/modules/data_engineering/application/commands/retry_stock_daily_sync_failures_handler.py`
- Test: `tests/unit/modules/data_engineering/application/commands/test_retry_stock_daily_sync_failures_handler.py`

**Step 1: Write failing test**
Test retry logic (success mark resolved, failure increment retry count) with mocked deps.

**Step 2: Run test to verify it fails**
Run: `pytest tests/unit/modules/data_engineering/application/commands/test_retry_stock_daily_sync_failures_handler.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**
Implement Command and Handler logic.

**Step 4: Run test to verify it passes**
Run: `pytest tests/unit/modules/data_engineering/application/commands/test_retry_stock_daily_sync_failures_handler.py -v`
Expected: PASS

**Step 5: Commit**
```bash
git add src/app/modules/data_engineering/application/commands/retry_stock_daily_sync_failures*.py tests/unit/modules/data_engineering/application/commands/test_retry_stock_daily_sync_failures_handler.py
git commit -m "feat(data_engineering): add retry failures command and handler"
```

---

## 7. Interface Layer

### Task 7.1: Add HTTP Routes and Dependencies

**Files:**
- Create: `src/app/modules/data_engineering/interfaces/api/stock_daily_router.py`
- Modify: `src/app/modules/data_engineering/interfaces/dependencies.py`
- Modify: `src/app/interfaces/module_registry.py`
- Test: `tests/api/modules/data_engineering/test_stock_daily_api.py`

**Step 1: Write failing test**
Test the 3 new endpoints using FastAPI `TestClient`.

**Step 2: Run test to verify it fails**
Run: `pytest tests/api/modules/data_engineering/test_stock_daily_api.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**
Implement router, update DI container to provide handlers, and register router in `module_registry.py`.

**Step 4: Run test to verify it passes**
Run: `pytest tests/api/modules/data_engineering/test_stock_daily_api.py -v`
Expected: PASS

**Step 5: Commit**
```bash
git add src/app/modules/data_engineering/interfaces/ src/app/interfaces/module_registry.py tests/api/modules/data_engineering/test_stock_daily_api.py
git commit -m "feat(data_engineering): add HTTP endpoints for stock daily sync"
```
