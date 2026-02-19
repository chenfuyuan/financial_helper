# 金融助手项目 —— DDD 与整洁架构全面评估报告

本文档基于对当前代码库的架构评估，给出坏味道诊断、目标目录树、分层解析及预留组件规范，供后续开发与重构参考。

---

## 一、代码坏味道诊断

按严重程度从高到低逐一拆解。

### 坏味道 #1：事务边界泄漏到 Interfaces 层（严重）

**位置**：`src/app/modules/data_engineering/interfaces/api/stock_basic_router.py`

```python
@router.post("/sync", response_model=ApiResponse[dict])
async def sync_stock_basic(
    uow: SqlAlchemyUnitOfWork = Depends(get_uow),
    handler: SyncStockBasicHandler = Depends(get_sync_stock_basic_handler),
) -> ApiResponse[dict]:
    start = time.perf_counter()
    synced_count = await handler.handle(SyncStockBasic())
    await uow.commit()   # ← 事务提交在 Router 中
    ...
```

**问题**：`uow.commit()` 出现在 Router（Interfaces 层）中。架构规则明确：**Application 层控制事务边界**。Router 只应负责 HTTP 编排，不应知道事务的存在。若同一 Handler 被 Celery Task 或 MQ Consumer 调用，需在每个入口重复 `uow.commit()`。

**应改为**：Handler 接收 UoW，在 `handle()` 内部控制 commit/rollback；Router 只做 `await handler.handle(command)` 并返回结果。

---

### 坏味道 #2：领域实体携带基础设施关注字段（严重）

**位置**：`src/app/modules/data_engineering/domain/entities/stock_basic.py`

```python
@dataclass(eq=False)
class StockBasic(Entity[int | None]):
    id: int | None
    created_at: datetime   # 持久化/审计
    updated_at: datetime    # 持久化/审计
    version: int           # 持久化/审计
    source: DataSource | str
    third_code: str
    ...
```

**问题**：`created_at`、`updated_at`、`version` 是**持久化/审计**关注点，不是领域概念。导致 Gateway Mapper 被迫在构建领域对象时填入这些值，领域层依赖了时间戳表示，破坏 Entity 的纯业务职责。

**应改为**：上述字段仅保留在 `StockBasicModel`（infrastructure 层）；领域实体只保留业务字段。

---

### 坏味道 #3：StockBasic 用 Entity 但拥有 Repository → 应为 AggregateRoot（中等）

**位置**：`domain/repositories/stock_basic_repository.py` 与 `domain/entities/stock_basic.py`

**问题**：DDD 规则是 **Repository 只服务 AggregateRoot**。`StockBasic` 继承 `Entity` 却拥有独立 Repository，与 `shared_kernel` 中 `Repository(AR, ID)` 且 `AR bound=AggregateRoot` 矛盾。

**应改为**：若需独立持久化，`StockBasic` 应继承 `AggregateRoot[int | None]`。

---

### 坏味道 #4：领域异常未继承 DomainException（中等）

**位置**：`src/app/modules/data_engineering/domain/exceptions.py`

```python
class ExternalStockServiceError(Exception):  # 应继承 DomainException
    pass
```

**问题**：直接继承 `Exception`，未纳入 `DomainException` 体系。全局异常处理器只对 `DomainException` 子类做统一响应，导致该异常会落入 `general_exception_handler`，返回笼统 500。

---

### 坏味道 #5：Router / Handler 中的 noqa 导入（轻微）

**位置**：`sync_stock_basic_handler.py`、`stock_basic_router.py`

```python
from app.modules.data_engineering import domain  # noqa: F401
from app.modules.data_engineering import application, infrastructure  # noqa: F401
```

**问题**：未使用导入为满足隐式依赖而保留，可读性差、脆弱。

---

### 坏味道 #6：值对象与实体混放（轻微）

**位置**：`domain/entities/stock_basic.py` 中 `StockStatus`、`DataSource` 与 `StockBasic` 同文件。

**问题**：违反「一文件一概念」；模块级 `domain/` 下缺少 `value_objects/` 目录。

---

### 坏味道 #7：缺少 CQRS 的 Query 侧结构

Application 层仅有 `commands/`，无 `queries/`。未来读操作（股票列表、搜索等）需预留结构。

---

### 坏味道 #8：SqlAlchemyStockBasicRepository 未继承 SqlAlchemyRepository 基类

`shared_kernel` 中已有 `SqlAlchemyRepository` 基类，但 `SqlAlchemyStockBasicRepository` 未继承，直接持 `AsyncSession`，导致基类闲置、各模块 Repository 风格不统一。

---

### 小结

| 维度       | 诊断 |
|------------|------|
| 分层边界   | 事务控制泄漏到 Interfaces；Entity 承载基础设施字段 |
| DDD 建模   | Entity vs AggregateRoot 使用不当；值对象未独立 |
| 异常体系   | 领域异常未继承 DomainException |
| SRP        | 文件内多概念混放；noqa 隐式耦合 |
| 扩展性     | 缺少 events、queries、services、tasks、cache 等扩展位 |

---

## 二、终极目录树设计

基于技术栈（FastAPI、SQLAlchemy、PostgreSQL、InfluxDB、Neo4j、Redis、Celery、LangGraph、Elasticsearch）与规划业务模块，目标结构如下。

```
financial_helper/
├── src/
│   └── app/
│       ├── __init__.py
│       ├── config.py                                 # pydantic-settings 全局配置
│       │
│       ├── shared_kernel/                            # 跨模块共享构建块
│       │   ├── __init__.py
│       │   ├── domain/                               # 领域层 — 基类与契约
│       │   │   ├── __init__.py
│       │   │   ├── aggregate_root.py
│       │   │   ├── entity.py
│       │   │   ├── value_object.py
│       │   │   ├── domain_event.py
│       │   │   ├── exception.py
│       │   │   ├── repository.py
│       │   │   └── unit_of_work.py
│       │   ├── application/
│       │   │   ├── __init__.py
│       │   │   ├── command.py
│       │   │   ├── command_handler.py
│       │   │   ├── query.py
│       │   │   ├── query_handler.py
│       │   │   ├── mediator.py
│       │   │   ├── event_bus.py                      # EventBus 抽象
│       │   │   └── dto.py                            # 可选
│       │   └── infrastructure/
│       │       ├── __init__.py
│       │       ├── database.py
│       │       ├── sqlalchemy_repository.py
│       │       ├── sqlalchemy_unit_of_work.py
│       │       ├── logging.py
│       │       ├── redis_client.py
│       │       ├── influxdb_client.py
│       │       ├── neo4j_client.py
│       │       ├── elasticsearch_client.py
│       │       ├── celery_app.py
│       │       └── event_bus_impl.py
│       │
│       ├── modules/
│       │   ├── data_engineering/
│       │   │   ├── __init__.py
│       │   │   ├── domain/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── entities/
│       │   │   │   │   ├── __init__.py
│       │   │   │   │   └── stock_basic.py
│       │   │   │   ├── value_objects/
│       │   │   │   │   ├── __init__.py
│       │   │   │   │   ├── stock_status.py
│       │   │   │   │   └── data_source.py
│       │   │   │   ├── gateways/
│       │   │   │   │   ├── __init__.py
│       │   │   │   │   └── stock_gateway.py
│       │   │   │   ├── repositories/
│       │   │   │   │   ├── __init__.py
│       │   │   │   │   └── stock_basic_repository.py
│       │   │   │   ├── services/
│       │   │   │   │   └── __init__.py
│       │   │   │   ├── events/
│       │   │   │   │   ├── __init__.py
│       │   │   │   │   └── stock_data_synced.py
│       │   │   │   └── exceptions.py
│       │   │   ├── application/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── commands/
│       │   │   │   │   ├── __init__.py
│       │   │   │   │   ├── sync_stock_basic.py
│       │   │   │   │   └── sync_stock_basic_handler.py
│       │   │   │   ├── queries/
│       │   │   │   │   ├── __init__.py
│       │   │   │   │   ├── get_stock_list.py
│       │   │   │   │   └── get_stock_list_handler.py
│       │   │   │   └── events/
│       │   │   │       ├── __init__.py
│       │   │   │       └── on_stock_data_synced.py
│       │   │   ├── infrastructure/
│       │   │   │   ├── __init__.py
│       │   │   │   ├── models/
│       │   │   │   │   ├── __init__.py
│       │   │   │   │   └── stock_basic_model.py
│       │   │   │   ├── gateways/
│       │   │   │   │   ├── __init__.py
│       │   │   │   │   ├── tushare_stock_gateway.py
│       │   │   │   │   └── mappers/
│       │   │   │   │       ├── __init__.py
│       │   │   │   │       └── tushare_stock_basic_mapper.py
│       │   │   │   ├── repositories/
│       │   │   │   │   ├── __init__.py
│       │   │   │   │   ├── sqlalchemy_stock_basic_repository.py
│       │   │   │   │   └── mappers/
│       │   │   │   │       ├── __init__.py
│       │   │   │   │       └── stock_basic_persistence_mapper.py
│       │   │   │   ├── cache/
│       │   │   │   │   ├── __init__.py
│       │   │   │   │   └── stock_basic_cache.py
│       │   │   │   └── tasks/
│       │   │   │       ├── __init__.py
│       │   │   │       └── sync_stock_basic_task.py
│       │   │   └── interfaces/
│       │   │       ├── __init__.py
│       │   │       ├── api/
│       │   │       │   ├── __init__.py
│       │   │       │   └── stock_basic_router.py
│       │   │       ├── consumers/
│       │   │       │   ├── __init__.py
│       │   │       │   └── stock_sync_consumer.py
│       │   │       ├── schedulers/
│       │   │       │   ├── __init__.py
│       │   │       │   └── daily_sync_scheduler.py
│       │   │       └── dependencies.py
│       │   │
│       │   ├── llm_gateway/
│       │   │   ├── domain/ (entities, value_objects, gateways, repositories, services, events, exceptions)
│       │   │   ├── application/ (commands, queries, events)
│       │   │   ├── infrastructure/ (models, gateways/mappers, repositories/mappers, cache, tasks)
│       │   │   └── interfaces/ (api, consumers, schedulers, dependencies.py)
│       │   │
│       │   ├── knowledge_center/
│       │   ├── market_insight/
│       │   ├── coordinator/
│       │   ├── research/
│       │   ├── debate/
│       │   └── judge/
│       │
│       └── interfaces/                               # 全局接口层
│           ├── __init__.py
│           ├── main.py
│           ├── dependencies.py
│           ├── exception_handler.py
│           ├── middleware.py
│           └── response.py
│
├── workers/
│   ├── __init__.py
│   ├── celery_worker.py
│   └── scheduler.py
│
├── migrations/
├── tests/
│   ├── conftest.py
│   ├── unit/
│   ├── integration/
│   ├── api/
│   └── architecture/
│
├── scripts/
├── docs/
├── guide/
├── pyproject.toml
├── Makefile
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
└── .env.example
```

---

## 三、架构与层级解析

### 3.1 分层依赖规则

```
    ┌─────────────────────────────────────────┐
    │           Interfaces 层（入站）           │  ← HTTP Router / MQ Consumer / Scheduler
    │  可 import: application, infrastructure  │
    └──────────────────┬──────────────────────┘
                       │ 依赖
    ┌──────────────────▼──────────────────────┐
    │           Application 层（用例）          │  ← Handler, Command, Query, DTO
    │  只可 import: domain                    │
    └──────────────────┬──────────────────────┘
                       │ 依赖
    ┌──────────────────▼──────────────────────┐
    │           Domain 层（核心）               │  ← Entity, AggregateRoot, ValueObject
    │  不 import 任何其他层                     │     DomainEvent, Repository接口, Gateway接口
    └──────────────────▲──────────────────────┘
                       │ 实现
    ┌──────────────────┴──────────────────────┐
    │         Infrastructure 层（出站）         │  ← ORM Model, DB实现, 外部API适配器
    │  只可 import: domain（实现其接口）        │     Cache实现, MQ Producer, Celery Task
    └─────────────────────────────────────────┘
```

### 3.2 各层职责与禁忌

#### Domain 层 — `modules/<name>/domain/`

| 目录           | 放什么                                                                 | 绝对不放什么 |
|----------------|------------------------------------------------------------------------|--------------|
| `entities/`    | 业务实体，`@dataclass(eq=False)`，仅业务属性和业务行为                  | `created_at`、`updated_at`、`version`；任何 `import sqlalchemy` |
| `value_objects/` | 不可变值对象、领域枚举，`_validate()` 校验                             | 可变状态；数据库类型引用 |
| `gateways/`    | 外部数据源抽象接口（ABC）                                              | HTTP 客户端、SDK 引用 |
| `repositories/` | 持久化抽象接口（ABC）                                                  | SQL、ORM 引用 |
| `services/`    | 跨实体的领域逻辑                                                       | 基础设施调用、HTTP 请求 |
| `events/`      | 领域事件定义（继承 `DomainEvent`）                                     | 事件处理逻辑（属 application 层） |
| `exceptions.py` | 领域异常，**必须**继承 `DomainException`                               | 直接继承 `Exception` |

#### Application 层 — `modules/<name>/application/`

| 目录        | 放什么                                                       | 绝对不放什么 |
|-------------|--------------------------------------------------------------|--------------|
| `commands/` | Command DTO + CommandHandler；Handler 内**控制事务边界**    | 直接操作 DB；HTTP 对象 |
| `queries/`  | Query DTO + QueryHandler；可绕过领域直接读库（CQRS 读侧）     | 写操作 |
| `events/`   | 领域事件处理器（订阅事件执行副作用）                          | 领域事件定义 |

**原则**：Handler 接收 UoW，在 `handle()` 内 `await uow.commit()`，不把事务权交给调用方。

#### Infrastructure 层 — `modules/<name>/infrastructure/`

| 目录            | 放什么                                                         | 绝对不放什么 |
|-----------------|----------------------------------------------------------------|--------------|
| `models/`       | SQLAlchemy ORM Model，含审计字段                               | 业务逻辑 |
| `gateways/`     | Gateway 接口实现 + `mappers/`（API 响应 → 领域实体）           | 业务判断逻辑 |
| `repositories/` | Repository 接口实现 + `mappers/`（领域实体 ⇄ ORM）              | 事务 commit |
| `cache/`        | 缓存策略实现（Redis 等）                                        | 业务失效策略（应在 application 定义） |
| `tasks/`        | Celery 任务定义，内部委托 Handler                               | 复杂业务逻辑 |

#### Interfaces 层 — `modules/<name>/interfaces/`

| 目录              | 放什么                                                         | 绝对不放什么 |
|-------------------|----------------------------------------------------------------|--------------|
| `api/`            | FastAPI Router，`Depends` 注入 Handler，包装 `ApiResponse`      | 业务逻辑、`uow.commit()`、SQL |
| `consumers/`      | MQ 消费者：解析消息 → Command → 委托 Handler                    | 业务逻辑 |
| `schedulers/`     | 定时任务触发点与 Command/Task 绑定                             | 具体业务逻辑 |
| `dependencies.py` | 模块内 DI 组装                                                 | 跨模块依赖（放全局 `app/interfaces/dependencies.py`） |

### 3.3 全局 vs 模块 Interfaces

- **`app/interfaces/`**：main、dependencies（DB/UoW/Mediator/Redis 等）、exception_handler、middleware、response。
- **`modules/<name>/interfaces/`**：api、consumers、schedulers、dependencies（模块内 DI）。

---

## 四、预留组件规范与调用流转

### 4.1 Celery 异步任务 (`infrastructure/tasks/`)

**场景**：股票同步耗时，异步执行。

**存放**：

- `infrastructure/tasks/sync_stock_basic_task.py` — 任务定义
- `interfaces/api/stock_basic_router.py` — HTTP 触发
- `interfaces/schedulers/daily_sync_scheduler.py` — 定时触发

**流转**：

```
HTTP POST /sync 或 Celery Beat
    → interfaces (Router / Scheduler)
    → infrastructure/tasks/sync_stock_basic_task.py
    → application/commands/sync_stock_basic_handler.py
        (gateway.fetch → repository.upsert → uow.commit，可选发布事件)
    → application/events/on_stock_data_synced.py（若需跨模块通知）
```

**任务模板要点**：在 task 内构建 UoW + Gateway + Repository + Handler，调用 `handler.handle(SyncStockBasic())`，不依赖 FastAPI 的 DI。

---

### 4.2 MQ 消费者 (`interfaces/consumers/`)

**场景**：其他系统/模块通过 MQ 通知执行同步。

**存放**：`interfaces/consumers/stock_sync_consumer.py`。

**流转**：解析消息 → 构造 `SyncStockBasic` → 委托 Handler。Consumer 只做协议解析 + Command 构造，与 Router 职责对称（入站适配器，协议不同）。

---

### 4.3 定时任务 (`interfaces/schedulers/`)

**场景**：每日凌晨定时同步。

**存放**：`interfaces/schedulers/daily_sync_scheduler.py` 定义调度；实际执行委托 `infrastructure/tasks/` 中的 Celery Task。

**示例**：`schedule` 中配置 `task` 路径与 crontab，由 Celery Beat 驱动。

---

### 4.4 缓存 (`infrastructure/cache/`)

**场景**：股票列表热数据 Redis 缓存。

**存放**：可选在 domain 定义缓存端口；`infrastructure/cache/stock_basic_cache.py` 实现。

**流转**：QueryHandler 先查 cache → 未命中则 repository 查询 → 回填 cache → 返回。Application 通过抽象使用缓存，不直接 `import redis`。

---

### 4.5 领域事件 (`domain/events/` + `application/events/`)

**场景**：同步完成后触发知识图谱更新。

**存放**：

- `domain/events/stock_data_synced.py` — 事件定义（纯数据，继承 `DomainEvent`）
- `application/events/on_stock_data_synced.py` — 事件处理器

**流转**：Handler 完成后 `event_bus.publish(StockDataSynced(...))` → EventBus 分发 → 各模块订阅者执行（如 knowledge_center 增量构建）。

---

### 4.6 外部 API 防腐层（ACL）

防腐层通过 **Gateway 接口 + Mapper** 实现，无需独立目录：

- `domain/gateways/stock_gateway.py` — 领域语言（如 `fetch_stock_basic`）
- `infrastructure/gateways/tushare_stock_gateway.py` + `mappers/tushare_stock_basic_mapper.py` — 适配器 + 翻译（TuShare 字段 → 领域模型）

新增数据源（如同花顺）时，仅新增对应 gateway 与 mapper，领域与应用层零改动。

---

## 五、总结图

```
┌──────────────────── 入站适配器 ────────────────────┐
│  HTTP Router  │  MQ Consumer  │  Scheduler/Cron    │  ← interfaces/
└───────┬───────┴───────┬───────┴────────┬───────────┘
        │               │                │
        ▼               ▼                ▼
┌──────────────── Application 层 ────────────────────┐
│  CommandHandler / QueryHandler / EventHandler       │
│  (编排领域对象 + 控制事务边界 + 发布事件)            │
└───────────────────────┬────────────────────────────┘
                        │
                        ▼
┌──────────────── Domain 层（纯净） ─────────────────┐
│  Entity / AggregateRoot / ValueObject / Service     │
│  DomainEvent / Repository接口 / Gateway接口         │
└───────────────────────▲────────────────────────────┘
                        │ 实现
┌──────────────── 出站适配器 ────────────────────────┐
│  SQLAlchemy Repo │ Redis Cache │ TuShare Gateway    │
│  Celery Task     │ Neo4j Repo  │ InfluxDB Repo      │  ← infrastructure/
└────────────────────────────────────────────────────┘
```

当前架构的四层分离、Mediator、Mapper 设计基础正确；主要需收紧**边界**：事务在 Application 层、实体不携带基础设施字段、异常统一继承 `DomainException`，并在各模块预留 events、queries、cache、tasks、consumers、schedulers 等扩展位。
