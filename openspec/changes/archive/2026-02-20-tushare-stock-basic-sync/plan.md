# TuShare 股票基础信息同步 — 实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在 data_engineering 模块中实现从 TuShare 拉取 A 股股票基础信息、以 (source, third_code) 幂等写入 PostgreSQL，并通过 POST /data-engineering/stock-basic/sync 按需触发；整批解析成功才落库，任一条解析失败则整次失败。

**Architecture:** DDD 四层（domain / application / infrastructure / interfaces）。领域实体 StockBasic + 网关接口 StockGateway + 仓储接口 StockBasicRepository（upsert_many）；应用层 SyncStockBasic 命令与 Handler 编排网关拉取 → 仓储 upsert → 事务提交；基础设施 TuShareStockGateway（全量解析或抛错）、SqlAlchemyStockBasicRepository（ON CONFLICT upsert）；接口层 FastAPI 路由，请求内 get_uow + 构造 Handler 后 handle + commit。表结构含基础字段 id、created_at、updated_at、version（见 CLAUDE.md 数据库设计规范）。

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy async + asyncpg, Alembic, pytest, structlog。TuShare 客户端（需在依赖中确认或添加）。

**参考:** 本变更的 [design.md](./design.md)、[specs/stock-basic-sync/spec.md](./specs/stock-basic-sync/spec.md)；项目 CLAUDE.md、`src/app/modules/example/` 与 `src/app/shared_kernel/`。

---

## Task 1: 模块骨架与 domain 实体、枚举

**Files:**
- Create: `src/app/modules/data_engineering/domain/__init__.py`（空或导出）
- Create: `src/app/modules/data_engineering/domain/stock_basic.py`
- Create: `src/app/modules/data_engineering/application/__init__.py`
- Create: `src/app/modules/data_engineering/application/commands/__init__.py`
- Create: `src/app/modules/data_engineering/infrastructure/__init__.py`
- Create: `src/app/modules/data_engineering/infrastructure/models/__init__.py`
- Create: `src/app/modules/data_engineering/interfaces/__init__.py`
- Create: `src/app/modules/data_engineering/interfaces/api/__init__.py`
- Modify: `pyproject.toml` — 在 importlinter `containers` 中追加 `app.modules.data_engineering`

**Step 1: 添加 data_engineering 到 import-linter**

在 `pyproject.toml` 的 `[tool.importlinter]` 下 `containers` 列表中追加：

```toml
"app.modules.data_engineering",
```

即保持现有 `app.shared_kernel`、`app.modules.example`，新增 `app.modules.data_engineering`。

**Step 2: 创建 domain 实体与枚举**

在 `src/app/modules/data_engineering/domain/stock_basic.py` 中实现：

- 枚举 `StockStatus`: `LISTED`, `DELISTED`, `SUSPENDED`。
- 枚举 `DataSource`: `TUSHARE`（值如 `"TUSHARE"`）。
- 实体 `StockBasic`：含基础字段 `id`（int | None）、`created_at`、`updated_at`、`version`；业务字段 `source`、`third_code`、`symbol`、`name`、`market`、`area`、`industry`、`list_date`、`status`。可使用 `dataclass` 或继承 `Entity`（若 id 为可选可不用 AggregateRoot）。领域内不依赖任何 infrastructure。

**Step 3: 创建各层 __init__.py**

创建上述列出的空 `__init__.py`，保证包可导入。

**Step 4: 运行架构与导入检查**

Run: `make architecture-check`  
Expected: 通过（或仅剩与 data_engineering 无关的告警）。

**Step 5: Commit**

```bash
git add src/app/modules/data_engineering/ pyproject.toml
git commit -m "feat(data_engineering): add module skeleton and StockBasic entity with enums"
```

---

## Task 2: domain 网关与仓储接口

**Files:**
- Create: `src/app/modules/data_engineering/domain/stock_gateway.py`
- Create: `src/app/modules/data_engineering/domain/stock_basic_repository.py`

**Step 1: 编写网关接口**

在 `stock_gateway.py` 中定义抽象类 `StockGateway`，方法：

- `async def fetch_stock_basic(self) -> list[StockBasic]`

返回领域对象列表；实现类负责拉取并解析，任一条解析失败即抛异常。

**Step 2: 编写仓储接口**

在 `stock_basic_repository.py` 中定义抽象类 `StockBasicRepository`，方法：

- `async def upsert_many(self, stocks: list[StockBasic]) -> None`

以 (source, third_code) 为唯一键批量 upsert；不 commit，由调用方 UnitOfWork 管理。

**Step 3: 运行检查**

Run: `make lint` 与 `make type-check`  
Expected: 通过。

**Step 4: Commit**

```bash
git add src/app/modules/data_engineering/domain/stock_gateway.py \
  src/app/modules/data_engineering/domain/stock_basic_repository.py
git commit -m "feat(data_engineering): add StockGateway and StockBasicRepository interfaces"
```

---

## Task 3: 单元测试 — StockBasic 与枚举

**Files:**
- Create: `tests/unit/modules/data_engineering/domain/__init__.py`
- Create: `tests/unit/modules/data_engineering/domain/test_stock_basic.py`

**Step 1: 写失败测试**

在 `test_stock_basic.py` 中写测试：构造 `StockBasic`，断言 `status` 为 `StockStatus` 枚举值、`list_date` 为 date、必填字段非空等（依你实体构造方式而定）。

**Step 2: 运行测试确认失败**

Run: `pytest tests/unit/modules/data_engineering/domain/test_stock_basic.py -v`  
Expected: 若实体未实现或签名不符则 FAIL。

**Step 3: 实现实体/枚举使测试通过**

回到 `domain/stock_basic.py`，确保 `StockStatus`、`DataSource`、`StockBasic` 字段与类型满足测试。

**Step 4: 运行测试确认通过**

Run: `pytest tests/unit/modules/data_engineering/domain/test_stock_basic.py -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/unit/modules/data_engineering/ domain/
git commit -m "test(data_engineering): unit tests for StockBasic entity"
```

---

## Task 4: SQLAlchemy 模型与迁移

**Files:**
- Create: `src/app/modules/data_engineering/infrastructure/models/stock_basic_model.py`
- Create: `migrations/versions/YYYYMMDD_HHMM_<revision>_add_stock_basic_table.py`（用 `make migrate-create msg="add stock_basic table"` 生成后编辑）

**Step 1: 编写 StockBasicModel**

在 `stock_basic_model.py` 中定义表 `stock_basic`，继承 `app.shared_kernel.infrastructure.database.Base`：

- 基础字段：`id`（PK，自增或 UUID）、`created_at`、`updated_at`、`version`（Integer，默认 0 或 1）。
- 业务字段：`source`、`third_code`、`symbol`、`name`、`market`、`area`、`industry`、`list_date`、`status`。
- `UniqueConstraint("source", "third_code")`。

**Step 2: 编写迁移**

Run: `make migrate-create msg="add stock_basic table"`  
然后编辑生成的 migration 文件：`op.create_table("stock_basic", ...)` 包含上述列及唯一约束。`downgrade` 中 `op.drop_table("stock_basic")`。

**Step 3: 运行迁移（本地有 DB 时）**

Run: `make migrate`  
Expected: upgrade 成功。

**Step 4: Commit**

```bash
git add src/app/modules/data_engineering/infrastructure/models/stock_basic_model.py migrations/
git commit -m "feat(data_engineering): add StockBasicModel and migration"
```

---

## Task 5: SqlAlchemyStockBasicRepository 实现

**Files:**
- Create: `src/app/modules/data_engineering/infrastructure/sqlalchemy_stock_basic_repository.py`
- Test: `tests/unit/modules/data_engineering/infrastructure/` 或 `tests/integration/`（见下）

**Step 1: 写失败测试（upsert_many 行为）**

在 `tests/integration/modules/data_engineering/` 下（或单测中用 aiosqlite 内存库）写测试：创建 repository，`upsert_many([StockBasic(...)])`，查询 session/DB 断言一行存在且 (source, third_code) 唯一；再次 `upsert_many` 同 (source, third_code) 不同 name，断言仅一行且 name 更新、version 递增、created_at 不变、updated_at 更新。

**Step 2: 运行测试确认失败**

Run: `pytest tests/integration/modules/data_engineering/ -v`（或你放的路径）  
Expected: FAIL（实现不存在或未满足断言）。

**Step 3: 实现 SqlAlchemyStockBasicRepository**

- 实现 `StockBasicRepository`，接收 `AsyncSession`，实现 `upsert_many`：使用 `ON CONFLICT (source, third_code) DO UPDATE` 设置业务字段及 `updated_at`、`version = version + 1`，插入时设 `version=0` 或 `1`、`created_at`/`updated_at` 为 now。
- `_to_entity(model) -> StockBasic`、实体转 model 的辅助（用于从 DB 读回验证）；upsert 可直接拼 INSERT...ON CONFLICT 或使用 SQLAlchemy `insert().on_conflict_do_update()`。

**Step 4: 运行测试确认通过**

Run: `pytest tests/integration/modules/data_engineering/ -v` 与 `make lint`、`make type-check`  
Expected: PASS.

**Step 5: Commit**

```bash
git add src/app/modules/data_engineering/infrastructure/sqlalchemy_stock_basic_repository.py tests/
git commit -m "feat(data_engineering): implement SqlAlchemyStockBasicRepository with upsert_many"
```

---

## Task 6: TuShare 网关实现与解析失败即抛

**Files:**
- Create: `src/app/modules/data_engineering/infrastructure/tushare_stock_gateway.py`
- Create: `src/app/modules/data_engineering/domain/exceptions.py`（可选，用于 ExternalStockServiceError）
- Test: `tests/unit/modules/data_engineering/infrastructure/test_tushare_stock_gateway.py`

**Step 1: 领域异常（可选）**

在 `domain/exceptions.py` 中定义 `ExternalStockServiceError`（或放在 shared_kernel 若项目已有约定），供网关解析/网络失败时抛出。

**Step 2: 写失败测试（字段映射 + 解析失败即抛）**

在 `test_tushare_stock_gateway.py` 中：用假数据（dict 或 DataFrame，模拟 TuShare 返回）构造网关或 mock 底层调用，断言 `fetch_stock_basic()` 返回的 `list[StockBasic]` 中 `ts_code`→`third_code`、`list_status` L/D/P→LISTED/DELISTED/SUSPENDED、`list_date` 字符串→date；再测一条 `list_date` 非法或必填缺失时 `fetch_stock_basic()` 抛出异常、不返回部分结果。

**Step 3: 运行测试确认失败**

Run: `pytest tests/unit/modules/data_engineering/infrastructure/test_tushare_stock_gateway.py -v`  
Expected: FAIL.

**Step 4: 实现 TuShareStockGateway**

- 依赖 TuShare 客户端（或 requests 调 API），调用 `stock_basic`；将返回逐条解析为 `StockBasic`，任一条解析失败（日期、必填、枚举不符）即抛出 `ExternalStockServiceError`（或同类）；全部成功则返回 `list[StockBasic]`。`source=DataSource.TUSHARE`。

**Step 5: 运行测试确认通过**

Run: `pytest tests/unit/modules/data_engineering/infrastructure/test_tushare_stock_gateway.py -v`  
Expected: PASS.

**Step 6: Commit**

```bash
git add src/app/modules/data_engineering/infrastructure/tushare_stock_gateway.py \
  src/app/modules/data_engineering/domain/exceptions.py tests/
git commit -m "feat(data_engineering): implement TuShareStockGateway, parse failure throws"
```

---

## Task 7: 命令与 Handler

**Files:**
- Create: `src/app/modules/data_engineering/application/commands/sync_stock_basic.py`
- Create: `src/app/modules/data_engineering/application/commands/sync_stock_basic_handler.py`
- Test: `tests/unit/modules/data_engineering/application/commands/test_sync_stock_basic_handler.py`

**Step 1: 命令对象**

在 `sync_stock_basic.py` 中定义 `SyncStockBasic`（dataclass, frozen），实现 `Command`（来自 shared_kernel）。

**Step 2: 写失败测试（Handler 编排）**

在 `test_sync_stock_basic_handler.py` 中：fake `StockGateway` 返回固定 `list[StockBasic]`，fake `StockBasicRepository` 记录 `upsert_many` 入参；构造 `SyncStockBasicHandler(gateway, repository)`，`await handler.handle(SyncStockBasic())`，断言 `repository.upsert_many` 被调用且参数与 gateway 返回一致；再测 gateway 抛异常时 handle 向上抛、repository.upsert_many 未被调用（或仅在不抛时调用）。

**Step 3: 运行测试确认失败**

Run: `pytest tests/unit/modules/data_engineering/application/commands/test_sync_stock_basic_handler.py -v`  
Expected: FAIL.

**Step 4: 实现 SyncStockBasicHandler**

- 依赖注入：`StockGateway`、`StockBasicRepository`。Handle：`stocks = await gateway.fetch_stock_basic()`，`await repository.upsert_many(stocks)`；不在此处 commit（由路由侧 UnitOfWork 管理）。返回值可为 `len(stocks)` 或小结构体（synced_count）供接口返回。

**Step 5: 运行测试确认通过**

Run: `pytest tests/unit/modules/data_engineering/application/commands/test_sync_stock_basic_handler.py -v`  
Expected: PASS.

**Step 6: Commit**

```bash
git add src/app/modules/data_engineering/application/commands/sync_stock_basic.py \
  src/app/modules/data_engineering/application/commands/sync_stock_basic_handler.py tests/
git commit -m "feat(data_engineering): SyncStockBasic command and handler"
```

---

## Task 8: 接口层 — 路由与依赖

**Files:**
- Create: `src/app/modules/data_engineering/interfaces/api/stock_basic_router.py`
- Modify: `src/app/interfaces/main.py`（include_router、注册 data_engineering 路由；若用 Mediator 则在此注册 SyncStockBasic 的 handler factory，否则在路由内构造 Handler + uow）

**Step 1: 写失败接口测试**

在 `tests/api/modules/data_engineering/` 下（或 `tests/api/` 中）用 FastAPI TestClient：POST `/data-engineering/stock-basic/sync`，mock 或 fake TuShare 网关返回固定 list；断言 2xx、响应体含 `synced_count`；再测网关抛异常时 5xx 或统一错误格式。

**Step 2: 实现路由**

在 `stock_basic_router.py` 中：  
- `POST /sync`：`async def sync_stock_basic(uow: SqlAlchemyUnitOfWork = Depends(get_uow))`；在路由内构造 `TuShareStockGateway(...)`、`SqlAlchemyStockBasicRepository(uow.session)`、`SyncStockBasicHandler(gateway, repo)`；`result = await handler.handle(SyncStockBasic())`；`await uow.commit()`；返回 `ApiResponse.success(data={"synced_count": result, "duration_ms": ...})`（可选耗时）。  
- 将 router 挂到 prefix `/data-engineering/stock-basic`，在 `main.py` 中 `app.include_router(data_engineering_router, prefix="/api/v1")` 或等价 prefix。

**Step 3: 在 main.py 中挂载路由**

在 `main.py` 中 import `stock_basic_router`（或 data_engineering 的 router 聚合），`app.include_router(..., prefix="/api/v1")`，确保路径为 `POST /api/v1/data-engineering/stock-basic/sync`（与 spec 一致则可能为 `/data-engineering/stock-basic/sync`，依你 API 前缀约定调整）。

**Step 4: 运行接口测试与 CI**

Run: `pytest tests/api/ -v` 与 `make ci`  
Expected: 通过。

**Step 5: Commit**

```bash
git add src/app/modules/data_engineering/interfaces/api/stock_basic_router.py src/app/interfaces/main.py tests/
git commit -m "feat(data_engineering): POST /data-engineering/stock-basic/sync route and integration"
```

---

## Task 9: 依赖与配置（TuShare token 等）

**Files:**
- Modify: `pyproject.toml` 或 `requirements.txt`（若需添加 tushare 或 requests）
- Create/Modify: `src/app/config.py` 或 settings — 增加 TUSHARE_TOKEN 或同类配置（从环境变量读取），供 TuShareStockGateway 使用

**Step 1: 添加 TuShare 依赖**

若项目未包含 TuShare，在 `pyproject.toml` 的 `dependencies` 中增加 `tushare`（或项目约定包名）。

**Step 2: 配置项**

在应用配置中增加 TuShare 所需项（如 API token），网关从配置或注入的 settings 读取，不硬编码。

**Step 3: 运行全量验证**

Run: `make ci`  
Expected: 通过。

**Step 4: Commit**

```bash
git add pyproject.toml src/app/config.py  # 或你放配置的文件
git commit -m "chore: add TuShare dependency and config"
```

---

## Task 10: 文档与收尾

**Files:**
- Modify: `openspec/changes/tushare-stock-basic-sync/` — 若需在 tasks 或 changelog 中记录“已实现”
- 可选：在 `docs/plans/financial-helper/modules/data-engineering.md` 中补充“已实现 stock_basic 同步”的简要说明

**Step 1: 运行完整 CI**

Run: `make ci`  
Expected: 全部通过。

**Step 2: 手动冒烟（可选）**

本地启动 `make dev`，对 `POST /api/v1/data-engineering/stock-basic/sync`（或实际路径）发请求，配置有效 TuShare token 时应返回 synced_count；或使用集成测试覆盖。

**Step 3: Commit 收尾**

```bash
git add openspec/changes/tushare-stock-basic-sync/  # 若有变更
git commit -m "docs: mark tushare-stock-basic-sync implementation complete"
```

---

## 执行方式说明

Plan 已保存到 `openspec/changes/tushare-stock-basic-sync/plan.md`。两种执行方式：

1. **Subagent-Driven（本会话）** — 按任务拆分子 agent，每步评审后再进行下一步，适合边做边改。
2. **Parallel Session（新会话）** — 在新会话中打开 executing-plans skill，在独立 worktree 中按检查点批量执行。

需要哪种方式？
