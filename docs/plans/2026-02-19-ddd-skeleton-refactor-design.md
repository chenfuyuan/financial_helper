# DDD + FastAPI 骨架全面重构设计

**日期：** 2026-02-19
**目标：** 将现有骨架重构为真正可用的 DDD + 整洁架构项目模板

---

## 1. 现状诊断

### 1.1 致命问题（阻塞使用）

**泛型/类型系统全面错误：**
- `Repository(ABC, Generic[AggregateRoot, Id])` — 用具体类名做泛型参数，遮蔽了导入的类
- `CommandHandler`、`QueryHandler` 同样的泛型遮蔽问题
- `SqlAlchemyRepository` 继承了错误的泛型
- `get_session()` 返回类型标注为 `AsyncSession`，实际是 `AsyncGenerator`

**DDD 核心概念缺失：**
- 无 `DomainEvent` 基类
- `AggregateRoot` 是空壳，无事件收集机制
- 无 `UnitOfWork` — 每个 `save()` 直接 `commit()`，无法控制事务边界
- 无 Mediator/Bus — CQRS 基类存在但无法串联

### 1.2 严重问题

- `asyncpg` 未声明为依赖（`psycopg` 与 `asyncpg` URL 不匹配）
- Dockerfile 中 `pip install -e .` 在源码 COPY 前执行
- CORS `allow_origins=["*"]` + `allow_credentials=True` 组合无效
- 健康检查不检查数据库连通性
- 数据库引擎在模块导入时创建，无法测试时替换

### 1.3 中等问题

- "ecommerce" 硬编码在 4 处（不适合通用模板）
- `.placeholder` 用隐藏目录名
- 缺少 README、Makefile、CI、pre-commit
- `scheduler.py` 空文件
- 所有 `__init__.py` 为空

---

## 2. 重构设计

### 2.1 领域层（shared_kernel/domain/）

**entity.py — 修正泛型**
- TypeVar `ID`（替代 `Id`）绑定 `Any`
- `__eq__` 使用 `type(self)` 精确比较

**domain_event.py — 新增**
- `DomainEvent` 基类，`frozen=True` dataclass
- 包含 `occurred_at: datetime` 字段

**aggregate_root.py — 增加事件收集**
- `_events: list[DomainEvent]` 内部列表
- `add_event(event)` / `collect_events()` 方法

**value_object.py — 增加验证钩子**
- `__post_init__` 调用 `_validate()` 抽象方法

**repository.py — 修正泛型**
- `AR = TypeVar("AR", bound=AggregateRoot)`，`ID = TypeVar("ID")`
- 移除 `find_all()`（ISP：按需在具体仓储定义）
- 保留 `find_by_id`、`save`、`delete`

**exception.py — 保持现有**，结构合理无需改动

### 2.2 应用层（shared_kernel/application/）

**command.py / query.py — 保持现有**

**command_handler.py / query_handler.py — 修正泛型**
- `C = TypeVar("C", bound=Command)`，`R = TypeVar("R")`
- `CommandHandler(ABC, Generic[C, R])`

**unit_of_work.py — 新增**
- 抽象 `UnitOfWork` 基类
- 支持 async context manager（`__aenter__` / `__aexit__`）
- `commit()` / `rollback()` 抽象方法

**mediator.py — 新增**
- 注册 command → handler_factory 映射
- 注册 query → handler_factory 映射
- `send(command)` 分发命令
- `query(query)` 分发查询
- handler_factory 模式支持 FastAPI 依赖注入

### 2.3 基础设施层（shared_kernel/infrastructure/）

**database.py — 重构为类**
- `Database` 类封装 engine + session_factory
- 延迟初始化（在 lifespan 中创建）
- `dispose()` 方法清理连接池
- `check_connection()` 方法供健康检查使用

**sqlalchemy_unit_of_work.py — 新增**
- 实现 `UnitOfWork`
- 管理 `AsyncSession` 生命周期
- `commit()` 时可收集聚合根事件并发布

**sqlalchemy_repository.py — 重构**
- 修正泛型参数
- `save()` 不再调用 `commit()`（由 UoW 管理）
- `_to_entity()` / `_to_model()` 保持为抽象方法

**logging.py — 小幅调整**，基本保持现有

### 2.4 接口层（interfaces/）

**main.py — 重构 lifespan**
- 在 lifespan 中初始化 `Database`、`Mediator`
- 注册示例模块的 handler
- 挂载到 `app.state`

**dependencies.py — 增强**
- `get_uow()` — 提供 UoW 实例
- `get_mediator()` — 提供 Mediator 实例
- `get_db()` — 提供 Database 实例

**middleware.py — CORS 配置化**
- origins 从 `Settings.CORS_ORIGINS` 读取

**response.py — 保持现有**

**exception_handler.py — 增加日志**
- 500 错误记录完整 traceback

**scheduler.py — 保持空文件或移除**

### 2.5 示例模块（modules/example/）

替代 `.placeholder/`，提供完整可运行的 CQRS 示例：

```
modules/example/
├── domain/
│   ├── note.py              # AggregateRoot: Note(id, title, content)
│   ├── note_created.py      # DomainEvent: NoteCreated
│   └── note_repository.py   # 仓储接口: NoteRepository
├── application/
│   ├── commands/
│   │   ├── create_note.py          # CreateNoteCommand
│   │   └── create_note_handler.py  # CreateNoteHandler
│   └── queries/
│       ├── get_note.py             # GetNoteQuery
│       └── get_note_handler.py     # GetNoteHandler
├── infrastructure/
│   ├── models/
│   │   └── note_model.py           # NoteModel (SQLAlchemy)
│   └── sqlalchemy_note_repository.py
└── interfaces/
    └── api/
        ├── note_router.py
        ├── requests/
        │   └── create_note_request.py
        └── responses/
            └── note_response.py
```

### 2.6 配置与依赖

**pyproject.toml：**
- 替换 `psycopg[binary,pool]` 为 `asyncpg`
- 确认所有依赖版本

**config.py：**
- `DATABASE_URL` 默认值使用 `myapp`
- 新增 `CORS_ORIGINS: list[str]`
- 新增 `LOG_LEVEL: str`

**alembic.ini：**
- 移除硬编码 URL（由 `env.py` 通过 settings 管理）

**.env.example：**
- 更新为通用配置

### 2.7 Docker 与部署

**Dockerfile — 多阶段构建：**
```dockerfile
# Stage 1: Builder
FROM python:3.11-slim AS builder
# 安装依赖到虚拟环境

# Stage 2: Runtime
FROM python:3.11-slim
# 只复制虚拟环境和源码，不含 dev 依赖
```

**docker-compose.yml：**
- 数据库名 `ecommerce` → `myapp`
- 增加 PostgreSQL 健康检查
- web 服务 depends_on 使用 health check 条件

### 2.8 工程化配套

| 文件 | 用途 |
|------|------|
| `Makefile` | dev, test, lint, format, migrate, docker-up/down |
| `.pre-commit-config.yaml` | ruff (lint + format), mypy |
| `.github/workflows/ci.yml` | lint → type-check → test |
| `README.md` | 项目说明、架构图、快速启动、开发指南 |

### 2.9 测试增强

**conftest.py：**
- 异步测试 fixture
- 内存 SQLite 或 test PostgreSQL 会话
- mock UoW factory
- mock Mediator factory

**示例测试：**
- `tests/unit/modules/example/domain/test_note.py` — 测试 Note 实体创建和领域事件
- `tests/unit/modules/example/application/test_create_note_handler.py` — 测试命令处理编排
- `tests/integration/test_sqlalchemy_uow.py` — 测试 UoW 与数据库协作

---

## 3. 目录结构（重构后）

```
project/
├── pyproject.toml
├── README.md
├── Makefile
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .gitignore
├── .env.example
├── .pre-commit-config.yaml
├── .github/
│   └── workflows/
│       └── ci.yml
├── alembic.ini
├── migrations/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── src/
│   └── app/
│       ├── __init__.py
│       ├── config.py
│       ├── shared_kernel/
│       │   ├── domain/
│       │   │   ├── entity.py
│       │   │   ├── value_object.py
│       │   │   ├── aggregate_root.py
│       │   │   ├── domain_event.py        # 新增
│       │   │   ├── repository.py
│       │   │   └── exception.py
│       │   ├── application/
│       │   │   ├── command.py
│       │   │   ├── query.py
│       │   │   ├── command_handler.py
│       │   │   ├── query_handler.py
│       │   │   ├── unit_of_work.py        # 新增
│       │   │   └── mediator.py            # 新增
│       │   └── infrastructure/
│       │       ├── database.py
│       │       ├── logging.py
│       │       ├── sqlalchemy_unit_of_work.py  # 新增
│       │       └── sqlalchemy_repository.py
│       ├── modules/
│       │   └── example/                   # 替代 .placeholder
│       │       ├── domain/
│       │       ├── application/
│       │       ├── infrastructure/
│       │       └── interfaces/
│       └── interfaces/
│           ├── main.py
│           ├── dependencies.py
│           ├── middleware.py
│           ├── exception_handler.py
│           └── response.py
└── tests/
    ├── conftest.py
    ├── unit/
    │   ├── shared_kernel/
    │   └── modules/
    │       └── example/
    │           ├── domain/          # 领域测试，如 test_note.py
    │           └── application/    # 应用层测试，如 test_create_note_handler.py
    └── integration/
        └── test_sqlalchemy_uow.py
```

---

## 4. 设计决策记录

| 决策 | 选择 | 理由 |
|------|------|------|
| 泛型命名 | `ID`, `AR`, `C`, `R` | 避免与具体类名冲突 |
| Repository 基类方法 | 只保留 find_by_id/save/delete | ISP：find_all 按需定义 |
| UoW 位置 | application 层（抽象）+ infrastructure 层（实现） | 依赖倒置 |
| Mediator 实现 | 自研轻量版 | 避免引入第三方依赖 |
| 示例实体 | Note（笔记） | 简单直观，足以展示完整流程 |
| 数据库初始化 | Database 类 + lifespan | 可测试、可替换 |
| Docker | 多阶段构建 | 生产镜像不含 dev 依赖 |
