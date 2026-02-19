# DDD + FastAPI Project Skeleton

A production-ready project skeleton based on **Domain-Driven Design (DDD)** and **Clean Architecture** principles.

## Tech Stack

- **Web Framework:** FastAPI
- **Database:** PostgreSQL + SQLAlchemy (async)
- **Migrations:** Alembic
- **Config:** pydantic-settings
- **Logging:** structlog
- **Testing:** pytest
- **Linting:** ruff + mypy

## Architecture

```
interfaces → application → domain ← infrastructure
```

| Layer | Responsibility |
|-------|---------------|
| **Domain** | Entities, Value Objects, Aggregate Roots, Repository interfaces, Domain Events |
| **Application** | Commands, Queries, Handlers, Unit of Work, Mediator |
| **Infrastructure** | SQLAlchemy models, Repository implementations, Database config |
| **Interfaces** | FastAPI routes, middleware, exception handling |

## Quick Start

```bash
# Clone and install
git clone <repo-url> && cd <project>
pip install -e ".[dev]"

# Set up environment
cp .env.example .env

# Start services
make docker-up

# Run migrations
make migrate

# Start dev server
make dev
```

## 使用本骨架创建新项目

要从本骨架开始一个**新项目**（独立 git 历史与远程），请参阅 **[docs/using-skeleton-for-new-project.md](docs/using-skeleton-for-new-project.md)**（中文）。其中说明：

- **方式一（推荐）：** GitHub「Use this template」— 无需 re-init git。
- **方式二：** Clone 本仓库后删除 `.git`、`git init`、首次提交并添加新项目的 `origin`。

## Project Structure

```
src/app/
├── shared_kernel/      # Shared base classes
│   ├── domain/         # Entity, ValueObject, AggregateRoot, Repository, DomainEvent
│   ├── application/    # Command, Query, Handlers, UnitOfWork, Mediator
│   └── infrastructure/ # Database, SqlAlchemy implementations
├── modules/            # Business modules (one per bounded context)
│   └── example/        # Example module demonstrating full CQRS flow
└── interfaces/         # FastAPI app entry point
```

## Development

```bash
make test           # Run tests
make lint           # Run linter
make format         # Format code
make type-check     # Run mypy
make migrate-create msg="add users table"  # Create migration
```

## Adding a New Module

1. Create `src/app/modules/<name>/domain/` — entities, events, repository interface
2. Create `src/app/modules/<name>/application/` — commands, queries, handlers
3. Create `src/app/modules/<name>/infrastructure/` — models, repository implementation
4. Create `src/app/modules/<name>/interfaces/api/` — router, requests, responses
5. Register handlers in `src/app/interfaces/main.py:_register_handlers()`
6. Include router in `main.py`
