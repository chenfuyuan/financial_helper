# 架构评估与全面升级方案

**日期：** 2026-02-20
**角色：** 资深架构师（DDD + Clean Architecture）
**目标：** 对 financial_helper 初始项目进行架构评估，并给出前瞻性的终极目录树设计

---

## 一、代码坏味道诊断

### 1.1 严重问题（必须修复）

#### 🔴 Bad Smell #1：领域模型类型不严格 — `StockBasic.source: DataSource | str`

**位置：** `src/app/modules/data_engineering/domain/entities/stock_basic.py:17`

```python
source: DataSource | str  # ← 坏味道
```

**问题：** 领域层的聚合根允许 `str` 类型的 `source`，这彻底破坏了值对象的类型安全保障。领域模型是系统的核心不变量，绝不应接受"非法"类型。`str` 应仅出现在基础设施层的映射转换中。

**修复：** `source` 严格定义为 `DataSource`，类型转换在 infrastructure 层的 Mapper 中完成。

---

#### 🔴 Bad Smell #2：`config.py` 与 `logging.py` 的隐式耦合

**位置：**
- `src/app/config.py` — 应用根级别的配置单例
- `src/app/shared_kernel/infrastructure/logging.py:7` — 直接 import `app.config`

```python
# logging.py
from app.config import settings  # ← infrastructure 层直接依赖应用根配置
```

**问题：** `shared_kernel/infrastructure/` 是被所有模块共享的基础设施层，它直接依赖 `app.config` 这个"应用层组装点"的配置单例。这违反了依赖倒置原则——基础设施层不应硬编码对应用配置入口的引用。这导致：
- `logging.py` 无法在不初始化完整 `Settings` 的环境下使用（如纯单元测试）
- 日志配置无法被替换或注入

**修复：** `configure_logging()` 改为接受参数注入，由 `main.py` 的 lifespan 传入。

---

#### 🔴 Bad Smell #3：`StockBasicRepository` 未继承 `Repository` 基类

**位置：** `src/app/modules/data_engineering/domain/repositories/stock_basic_repository.py`

```python
class StockBasicRepository(ABC):  # ← 未继承 shared_kernel 的 Repository
    @abstractmethod
    async def upsert_many(self, stocks: list[StockBasic]) -> None: ...
```

**问题：** `shared_kernel/domain/repository.py` 定义了 `Repository[AR, ID]` 泛型基类（含 `find_by_id`, `save`, `delete`），但 `StockBasicRepository` 完全绕开了它，自行定义 ABC。这说明通用 `Repository` 基类的接口过于僵化，无法覆盖"批量 upsert"这类真实业务场景。

**根因：** 仓储基类假设所有聚合根只需单条 CRUD，但金融数据领域常见批量操作。

**修复：** 允许模块仓储在继承 `Repository` 基类的基础上扩展方法，或明确在规范中声明：模块仓储接口可独立定义（当通用 CRUD 不适用时）。当前做法（独立 ABC）其实是务实选择，但需要在规范文档中明确这一点，避免后续开发者困惑。

---

### 1.2 中等问题（建议修复）

#### 🟡 Bad Smell #4：`main.py` 硬编码模块注册

**位置：** `src/app/interfaces/main.py:17-18, 67`

```python
from app.modules.data_engineering.interfaces.api.stock_basic_router import router as stock_basic_router
# ...
app.include_router(stock_basic_router, prefix="/api/v1")
```

**问题：** 每新增一个模块，都必须手动修改 `main.py` 添加 import 和 router 注册。当模块增长到 8-10 个时，`main.py` 会变成一个臃肿的"注册中心"。

**修复：** 引入模块注册器模式，每个模块提供一个 `register(app)` 函数，`main.py` 通过统一入口遍历注册。

---

#### 🟡 Bad Smell #5：全局 `settings` 单例模式

**位置：** `src/app/config.py:20`

```python
settings = Settings()  # ← 模块级单例
```

**问题：** 模块级单例在测试中难以替换。多处代码直接 `from app.config import settings`，使得测试必须通过 `monkeypatch` 修改环境变量或属性。

**影响：** 当前项目简单时可接受，但随着测试量增长（金融级项目需大量测试），会成为测试编写的障碍。暂不修改，但需在路线图中标记。

---

#### 🟡 Bad Smell #6：缺少模块级 `__init__.py` 导出清单

**问题：** 多数 `__init__.py` 为空，没有定义 `__all__` 或显式导出。良好的做法是在每层的 `__init__.py` 中明确导出公共 API，作为该层的"门面"。已做好的反面例子是 `domain/gateways/__init__.py` 和 `domain/repositories/__init__.py`——它们正确导出了公共接口。

---

### 1.3 轻微问题（可接受但值得关注）

#### ⚪ Bad Smell #7：`StrEnum` 值对象未继承 `ValueObject`

`DataSource` 和 `StockStatus` 使用 `StrEnum` 而非 `ValueObject` 基类。这是 Python 社区的务实选择——枚举天然不可变且可比较，功能上等同于值对象。但与 `guide/development-conventions.md` 中"值对象继承 `ValueObject`"的规范不一致。

**建议：** 在规范中明确：**枚举类型的值对象允许使用 `StrEnum`/`IntEnum`**，仅复合值对象需继承 `ValueObject`。

#### ⚪ Bad Smell #8：`SqlAlchemyRepository` 基类存在但使用率低

`SqlAlchemyStockBasicRepository` 虽然继承了 `SqlAlchemyRepository`，但主要业务方法 `upsert_many` 完全绕开了基类的 `save`/`find_by_id`/`delete`。基类提供的通用方法几乎未被使用。

**建议：** 保留基类，但不要求所有仓储都必须通过基类实现。基类作为"快速起步"工具，复杂场景允许覆盖。

---

## 二、终极目录树设计

以下是面向未来的完整目标项目结构。`★` 标记为本次新增/调整项。

```
financial_helper/
├── docs/                                  # 项目文档
│   ├── design/                            # 设计文档（按模块组织）
│   │   └── financial-helper/              # 系统设计文档集
│   ├── plans/                             # 技术方案
│   └── architecture-review-and-upgrade.md # ★ 本文档
│
├── guide/                                 # 开发规范
│   ├── architecture.md                    # 架构规则
│   ├── development-conventions.md         # 开发约定
│   └── testing.md                         # 测试规则
│
├── migrations/                            # Alembic 数据库迁移
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
│
├── scripts/                               # 工具脚本
│   └── new_module.py                      # 模块脚手架
│
├── src/app/                               # 源代码根
│   ├── config.py                          # 全局配置（pydantic-settings）
│   │
│   ├── shared_kernel/                     # ═══ 跨模块共享构建块 ═══
│   │   ├── domain/                        # 领域基类
│   │   │   ├── aggregate_root.py          # AggregateRoot[ID]
│   │   │   ├── entity.py                  # Entity[ID]
│   │   │   ├── value_object.py            # ValueObject
│   │   │   ├── domain_event.py            # DomainEvent
│   │   │   ├── exception.py               # DomainException, NotFoundException, ValidationException
│   │   │   ├── repository.py              # Repository[AR, ID] 通用仓储接口
│   │   │   └── unit_of_work.py            # UnitOfWork 抽象
│   │   │
│   │   ├── application/                   # 应用层基类
│   │   │   ├── command.py                 # Command
│   │   │   ├── command_handler.py         # CommandHandler[C, R]
│   │   │   ├── query.py                   # Query
│   │   │   ├── query_handler.py           # QueryHandler[Q, R]
│   │   │   ├── mediator.py               # Mediator（命令/查询分发）
│   │   │   ├── event_bus.py               # EventBus 抽象
│   │   │   └── dto.py                     # DTO 基类
│   │   │
│   │   └── infrastructure/                # 基础设施基类
│   │       ├── database.py                # Database + Base (SQLAlchemy)
│   │       ├── sqlalchemy_repository.py   # SqlAlchemyRepository 通用实现
│   │       ├── sqlalchemy_unit_of_work.py # SqlAlchemyUnitOfWork
│   │       ├── logging.py                 # ★ 结构化日志（参数注入，不直接依赖 config）
│   │       ├── cache.py                   # ★ 缓存客户端抽象（Redis 等）
│   │       ├── message_bus.py             # ★ 消息总线抽象（Celery/RabbitMQ 等）
│   │       └── scheduler.py               # ★ 定时任务调度器抽象
│   │
│   ├── modules/                           # ═══ 业务模块（限界上下文）═══
│   │   │
│   │   └── <module_name>/                 # 每个模块独立四层
│   │       ├── domain/                    # ─── 领域层（纯业务、零依赖）───
│   │       │   ├── entities/              # 聚合根 + 实体
│   │       │   ├── value_objects/         # 值对象（含 StrEnum）
│   │       │   ├── events/                # 领域事件定义
│   │       │   ├── gateways/              # 外部服务接口（出站端口）
│   │       │   ├── repositories/          # 仓储接口（出站端口）
│   │       │   ├── services/              # 领域服务
│   │       │   └── exceptions.py          # 领域异常
│   │       │
│   │       ├── application/               # ─── 应用层（用例编排）───
│   │       │   ├── commands/              # 命令 + Handler
│   │       │   ├── queries/               # 查询 + Handler
│   │       │   ├── events/                # 领域事件处理器（跨聚合/跨模块副作用）
│   │       │   └── dtos/                  # ★ 应用层 DTO（可选，复杂查询结果）
│   │       │
│   │       ├── infrastructure/            # ─── 基础设施层（技术实现）───
│   │       │   ├── models/                # SQLAlchemy ORM 模型
│   │       │   ├── repositories/          # 仓储实现
│   │       │   │   └── mappers/           # 持久化映射（Entity ↔ Model）
│   │       │   ├── gateways/              # 外部服务实现（防腐层 ACL）
│   │       │   │   └── mappers/           # 网关映射（外部 DTO → Entity）
│   │       │   ├── cache/                 # ★ 缓存策略实现
│   │       │   └── tasks/                 # ★ 异步任务（Celery task 定义）
│   │       │
│   │       └── interfaces/                # ─── 接口层（入站适配器）───
│   │           ├── api/                   # HTTP 路由（FastAPI Router）
│   │           ├── consumers/             # ★ MQ 消费者（入站消息处理）
│   │           ├── schedulers/            # ★ 定时任务触发器（Cron 入口）
│   │           └── dependencies.py        # 模块内 DI 组装
│   │
│   └── interfaces/                        # ═══ 全局接口层 ═══
│       ├── main.py                        # FastAPI 应用 + lifespan
│       ├── dependencies.py                # 跨模块共享依赖（DB, UoW, Mediator）
│       ├── exception_handler.py           # 统一异常处理
│       ├── middleware.py                   # 中间件
│       ├── response.py                    # ApiResponse 统一响应
│       └── module_registry.py             # ★ 模块注册器（自动注册 Router 等）
│
├── tests/                                 # 测试
│   ├── unit/                              # 纯逻辑，无外部依赖
│   │   ├── shared_kernel/
│   │   └── modules/<name>/
│   │       ├── domain/
│   │       ├── application/
│   │       └── infrastructure/
│   ├── integration/                       # 多层协作，测试数据库
│   │   └── modules/<name>/
│   ├── api/                               # HTTP 接口测试
│   │   └── modules/<name>/
│   └── architecture/                      # 架构守护测试
│
├── CLAUDE.md                              # AI 工作指南
├── Makefile                               # 常用命令
├── pyproject.toml                         # 项目配置
├── alembic.ini                            # Alembic 配置
├── docker-compose.yml                     # Docker 编排
├── Dockerfile
└── .env.example                           # 环境变量模板
```

---

## 三、架构与层级解析

### 3.1 分层依赖规则

```
interfaces → application → domain ← infrastructure
              ↑                       ↑
              └───────────────────────┘
                   (同级，不互依赖)
```

- **依赖方向**：外层 → 内层，永远不可逆
- **domain 层**：系统核心，零外部依赖
- **application 与 infrastructure**：同级，但 application 只依赖 domain，infrastructure 实现 domain 定义的接口
- **interfaces**：最外层，可依赖 application + infrastructure（用于组装依赖注入）

### 3.2 各层职责与禁区

#### 🟢 Domain 层 — 业务真相的唯一来源

| 允许放置 | 绝对禁止 |
|---------|---------|
| 聚合根、实体、值对象 | SQLAlchemy、FastAPI、任何框架 import |
| 领域事件定义 | HTTP 请求/响应对象 |
| 仓储/网关 **接口**（ABC） | 具体数据库操作 |
| 领域服务（纯业务规则） | 配置文件引用 |
| 领域异常 | 日志记录（structlog 等） |

**核心原则：** Domain 层可以脱离所有框架独立编译和测试。

#### 🔵 Application 层 — 用例编排

| 允许放置 | 绝对禁止 |
|---------|---------|
| Command / Query 定义 | 直接数据库操作 |
| CommandHandler / QueryHandler | HTTP 路由定义 |
| 事件处理器 | 框架特定注解（如 @router） |
| DTO（复杂查询结果封装） | 直接实例化基础设施类 |
| 调用 UoW.commit() 控制事务 | 直接 import 具体 Repository 实现 |

**核心原则：** 编排输入（Command）→ 领域操作 → 输出（返回值），通过接口依赖基础设施。

#### 🟠 Infrastructure 层 — 技术细节实现

| 允许放置 | 绝对禁止 |
|---------|---------|
| SQLAlchemy Model + Repository 实现 | 业务规则判断 |
| 外部 API 网关实现（防腐层） | 直接修改领域实体状态 |
| 缓存策略实现 | 直接返回 HTTP 响应 |
| 消息队列 Producer/Consumer 实现 | 定义领域事件 |
| Mapper（Entity ↔ Model / 外部 DTO） | import application 层 |

**核心原则：** 实现 Domain 层定义的接口，将技术细节隔离在此层。

#### 🟣 Interfaces 层 — 外部世界的入口

| 允许放置 | 绝对禁止 |
|---------|---------|
| FastAPI Router（HTTP 入口） | 业务逻辑 |
| MQ Consumer 入口 | 直接数据库操作 |
| Cron 定时任务入口 | 直接实例化 Repository |
| 依赖注入组装 | 事务控制（不调 uow.commit()） |
| 请求/响应 Pydantic Model | 领域事件定义 |

**核心原则：** 只做"翻译"——将外部请求翻译为 Command/Query，将结果翻译为 HTTP 响应。

---

## 四、预留组件说明与调用流转

### 4.1 分布式缓存（Cache）

**存放规范：**
- **抽象：** `shared_kernel/infrastructure/cache.py` — 定义 `CacheClient` 接口
- **模块实现：** `modules/<name>/infrastructure/cache/` — 模块特定的缓存策略

**调用流转示例（股票行情缓存）：**

```
Router (interfaces)
  → QueryHandler (application)
    → CachedStockRepository (infrastructure/cache/)
      → 命中缓存? → 直接返回
      → 未命中? → StockRepository (infrastructure/repositories/)
                  → 写入缓存 → 返回
```

### 4.2 消息队列（MQ Producer / Consumer）

**存放规范：**
- **消息总线抽象：** `shared_kernel/infrastructure/message_bus.py`
- **任务定义（Producer）：** `modules/<name>/infrastructure/tasks/` — Celery task
- **消费入口（Consumer）：** `modules/<name>/interfaces/consumers/` — 入站消息处理

**调用流转示例（异步数据同步）：**

```
[生产端]
Router POST /sync (interfaces/api/)
  → Handler 发布异步任务 (application)
    → MessageBus.publish(SyncStockTask) (infrastructure/tasks/)

[消费端]
Consumer (interfaces/consumers/)
  → 收到消息 → 构造 Command
  → Handler.handle(command) (application)
    → Gateway.fetch() → Repository.upsert() → UoW.commit()
```

### 4.3 定时任务（Cron / Scheduler）

**存放规范：**
- **调度器抽象：** `shared_kernel/infrastructure/scheduler.py`
- **触发入口：** `modules/<name>/interfaces/schedulers/` — 定义 cron 表达式 + 触发逻辑

**调用流转示例（每日收盘同步）：**

```
Scheduler Trigger (interfaces/schedulers/daily_sync.py)
  → 构造 SyncStockBasic Command
  → Handler.handle(command) (application)
    → Gateway.fetch() → Repository.upsert() → UoW.commit()
```

**关键原则：** Scheduler 触发器仅负责"何时触发"，具体"做什么"由 Application 层的 Handler 决定。同一个 Handler 可被 HTTP Router、MQ Consumer、Scheduler 共同复用。

### 4.4 领域事件总线（Event Bus）

**存放规范：**
- **抽象：** `shared_kernel/application/event_bus.py`（已存在）
- **事件定义：** `modules/<name>/domain/events/` — 领域事件
- **事件处理：** `modules/<name>/application/events/` — 事件处理器
- **实现：** `shared_kernel/infrastructure/` — InMemoryEventBus / CeleryEventBus

**调用流转示例（股票同步完成 → 通知知识图谱更新）：**

```
SyncStockBasicHandler (data_engineering/application)
  → stocks = gateway.fetch() → repository.upsert()
  → aggregate.add_event(StockBasicSynced(...))
  → uow.commit()  ← commit 后自动 dispatch events

EventBus.dispatch(StockBasicSynced)
  → KnowledgeGraphUpdateHandler (knowledge_center/application/events/)
    → 更新知识图谱
```

### 4.5 外部金融 API 防腐层（ACL / Gateway）

**存放规范：**
- **领域接口：** `modules/<name>/domain/gateways/` — 定义业务语义的接口
- **基础设施实现：** `modules/<name>/infrastructure/gateways/` — 对接具体 API
- **映射器：** `modules/<name>/infrastructure/gateways/mappers/` — 外部 DTO → 领域模型

**关键原则：** 当更换数据源（如 TuShare → 东方财富），只需在 `infrastructure/gateways/` 新增实现 + mapper，领域层和应用层零改动。当前项目的 `TuShareStockGateway` + `TuShareStockBasicMapper` 已是这一模式的良好实践。

---

## 五、优化执行清单

以下为本次架构升级的具体执行项：

| # | 优化项 | 优先级 | 影响范围 |
|---|--------|--------|---------|
| 1 | 修复 `StockBasic.source` 类型为严格 `DataSource` | 高 | domain + infrastructure mapper |
| 2 | `logging.py` 解耦 config 依赖，改为参数注入 | 高 | shared_kernel + main.py |
| 3 | 引入模块注册器 `module_registry.py` | 中 | interfaces/main.py |
| 4 | 补全预留目录 + 占位 `__init__.py` | 中 | 全项目结构 |
| 5 | 更新 `development-conventions.md` 反映新约定 | 中 | guide/ |

---

*本文档由架构评估生成，作为项目架构升级的参考基准。*
