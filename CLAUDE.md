# CLAUDE.md

## 项目

DDD + 整洁架构的 FastAPI WebAPI 项目骨架。通用模板，不绑定特定业务。

**技术栈:** Python 3.11, FastAPI, SQLAlchemy (async + asyncpg), PostgreSQL, Alembic, pydantic-settings, structlog, pytest

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

- `docs/plans/` — 设计文档和实施计划
- `docs/scaffold-new-module.md` — 新模块脚手架（make new-module）
- `docs/using-skeleton-for-new-project.md` — 从骨架创建新项目（Git 初始化与两种用法）
- `.cursor/rules/` — Cursor 分场景规则（架构、测试、工作流）
