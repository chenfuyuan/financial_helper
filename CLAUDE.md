# CLAUDE.md

## 项目

**金融助手系统** - 基于 DDD + 整洁架构的 A 股投资顾问系统，提供数据抓取、LLM 分析、知识图谱、每日复盘等核心功能。

**技术栈:** Python 3.11, FastAPI, SQLAlchemy (async + asyncpg), PostgreSQL, InfluxDB, Neo4j, Redis, Celery, LangGraph, Elasticsearch, Alembic, pydantic-settings, structlog, pytest

## 设计文档索引

在开始任何开发工作前，请先查阅相关设计文档。文档已按模块化拆分，按需读取：

### 核心文档（必读）
- `docs/plans/financial-helper/README.md` - 设计文档总索引 + AI 使用指南
- `docs/plans/financial-helper/01-overview.md` - 项目概述、技术栈、整体架构、数据流
- `docs/plans/financial-helper/02-dependencies.md` - 依赖关系图、模块边界约束

### 模块文档（按需要读取）
实现特定模块时，请读取对应的模块设计文档：
- `docs/plans/financial-helper/modules/foundation.md` - 基础设施层
- `docs/plans/financial-helper/modules/data-engineering.md` - 数据工程层
- `docs/plans/financial-helper/modules/llm-gateway.md` - LLM 网关层
- `docs/plans/financial-helper/modules/knowledge-center.md` - 知识中心
- `docs/plans/financial-helper/modules/market-insight.md` - 市场洞察
- `docs/plans/financial-helper/modules/coordinator.md` - 协调器（LangGraph 流程编排）
- `docs/plans/financial-helper/modules/research.md` - 研究模块
- `docs/plans/financial-helper/modules/debate.md` - 辩论模块
- `docs/plans/financial-helper/modules/judge.md` - 决策模块

### 横向关注点（按需要读取）
- `docs/plans/financial-helper/cross-cutting/error-handling.md` - 错误处理策略
- `docs/plans/financial-helper/cross-cutting/testing.md` - 测试策略
- `docs/plans/financial-helper/cross-cutting/security.md` - 安全设计
- `docs/plans/financial-helper/cross-cutting/performance.md` - 性能优化策略
- `docs/plans/financial-helper/cross-cutting/operations.md` - 运维与监控

### AI 工作流建议
1. **实现新功能**：先读对应模块文档 + 02-dependencies.md + 01-overview.md
2. **编写测试**：先读 cross-cutting/testing.md + 对应模块文档
3. **优化性能**：先读 cross-cutting/performance.md
4. **架构检查**：先读 02-dependencies.md 了解约束规则

## 架构

```
interfaces → application → domain ← infrastructure
```

- **domain** — 实体、值对象、聚合根、仓储接口、领域事件。零外部依赖。
- **application** — Command/Query + Handler（CQRS）、UnitOfWork、Mediator。编排用例，不含业务规则。
- **infrastructure** — SQLAlchemy 模型、仓储实现、数据库配置。实现 domain 层接口。
- **interfaces** — FastAPI 路由、中间件、异常处理、统一响应。

## 目录

```
src/app/
├── shared_kernel/           # 所有模块共用的基类
│   ├── domain/              # Entity, ValueObject, AggregateRoot, Repository, DomainEvent
│   ├── application/         # Command, Query, Handler, UnitOfWork, Mediator
│   └── infrastructure/      # Database, SqlAlchemyRepository, SqlAlchemyUnitOfWork
├── modules/<name>/          # 业务模块（每个限界上下文一个）
│   ├── domain/              # 聚合根、事件、仓储接口
│   ├── application/         # commands/ + queries/
│   ├── infrastructure/      # models/ + 仓储实现
│   └── interfaces/api/      # router, requests/, responses/
└── interfaces/              # FastAPI 入口 (main.py, dependencies.py)
```

## 命令

```bash
make dev              # uvicorn 开发服务器
make test             # pytest tests/ -v
make lint             # ruff check
make format           # ruff format + fix
make type-check       # mypy src/
make ci               # 与 CI 一致：lint + format check + type-check + architecture-check + test（提交前运行）
make architecture-check  # 架构守护：lint-imports + pytest tests/architecture/
make migrate          # alembic upgrade head
make migrate-create msg="描述"
make new-module name=<模块名>  # 从 example 生成新模块脚手架，见 docs/scaffold-new-module.md
make docker-up        # docker compose up -d --build
```

## 数据库设计规范

所有持久化对象（表）必须包含以下**基础字段**，用于主键、审计与乐观锁：

- **id** — 主键（自增或 UUID，依项目约定）。
- **created_at** — 创建时间（写入时设置，更新时不变）。
- **updated_at** — 更新时间（每次更新时刷新）。
- **version** — 版本号（建议从 0 或 1 起；更新时递增，用于乐观锁，可选但推荐）。

业务表在以上基础字段之外再增加业务字段；迁移与 SQLAlchemy 模型需显式包含上述四类字段。

## 关键约束

- **单一职责**: 一个文件 = 一个类/函数/概念。不要 `dtos.py`、`utils.py`。
- **依赖方向**: domain 不 import 其他层。违反即架构腐化。
- **事务边界**: Repository 不 commit，由 UnitOfWork 统一管理。
- **TDD**: 先写失败测试 → 最小实现 → 通过 → commit。

## 架构守护

- 层内依赖由 **import-linter** 检查（`lint-imports`）；Handler 位置与 domain 实体/值对象继承由 **tests/architecture/** 的 pytest 检查。
- 违反会导致 `make ci` 与 pre-commit 失败，需修复后才能合入。
- 新模块沿用 `domain/application/infrastructure/interfaces` 目录即可被守护；若使用枚举 container，需在 `pyproject.toml` 的 import-linter `containers` 中追加 `app.modules.<name>`。

## 测试

- `tests/unit/` — 纯领域逻辑，mock 外部依赖
  - `shared_kernel/` — 对应 `app/shared_kernel/`
  - `modules/<name>/` — 对应 `app/modules/<name>/`，**模块内按子目录**：`domain/`、`application/`（与源码一致）
- `tests/integration/` — 多层协作，aiosqlite 内存数据库
- `tests/api/` — 接口测试，HTTP 调 FastAPI，内存 SQLite，示例见 `tests/api/modules/example/`
- 运行: `python -m pytest tests/ -v`

## 验证（提交前必须通过）

与 GitHub Actions CI 一致，提交/推送前本地跑一遍：

```bash
make ci
```

等价于：`ruff check` + `ruff format --check` + `mypy` + `make architecture-check` + `pytest`。也可拆开：`make test && make lint && make type-check`，但 `make ci` 会多检查 `ruff format --check` 与架构守护，与 CI 完全一致。

## 参考文档

- `docs/plans/financial-helper/` — 金融助手系统设计文档（已模块化拆分）
- `docs/plans/financial-helper/README.md` — 设计文档总索引（必读）
- `.cursor/rules/` — Cursor 分场景规则（架构、测试、工作流）
