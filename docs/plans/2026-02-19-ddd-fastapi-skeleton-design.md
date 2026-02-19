# DDD + FastAPI 项目骨架设计文档

**日期：** 2026-02-19
**作者：** 超级Python架构师

## 1. 设计思想

### 1.1 领域驱动设计 (DDD)
- **分层架构**：领域层、应用层、基础设施层、接口层
- **聚合根**：保证业务一致性边界
- **值对象**：通过属性值定义身份的不可变对象
- **仓储模式**：封装数据持久化逻辑
- **领域事件**：领域内重要事件的发布与订阅

### 1.2 整洁架构
- **依赖规则**：内层不依赖外层，依赖方向向内
- **关注点分离**：每层只负责自己的职责
- **可测试性**：业务逻辑不依赖外部框架，易于单元测试

### 1.3 SOLID 原则
- **单一职责原则 (SRP)**：每个文件/类只做一件事
- **开闭原则 (OCP)**：对扩展开放，对修改关闭
- **里氏替换原则 (LSP)**：子类可以替换父类
- **接口隔离原则 (ISP)**：不依赖不需要的接口
- **依赖倒置原则 (DIP)**：依赖抽象，不依赖具体实现

---

## 2. 项目概述

基于 DDD（领域驱动设计）+ 整洁架构思想的 FastAPI WebAPI 项目骨架，使用 PostgreSQL 作为数据库，SQLAlchemy 作为 ORM。

## 2. 技术选型

| 组件 | 技术选型 |
|------|---------|
| Web 框架 | FastAPI |
| 数据库 | PostgreSQL |
| ORM | SQLAlchemy (异步) |
| 数据库迁移 | Alembic |
| 配置管理 | pydantic-settings |
| 日志 | structlog |
| 测试 | pytest |
| 包管理 | conda |
| 部署 | Docker + Docker Compose |

## 3. 完整目录结构

```
project-skeleton/
├── pyproject.toml                    # 项目元数据
├── README.md                          # 项目说明
├── environment.yml                    # conda 环境配置
├── Dockerfile                         # Docker 镜像构建
├── docker-compose.yml                 # Docker Compose 编排
├── .dockerignore
├── .env.example                       # 环境变量示例
├── .gitignore
├── alembic.ini                        # Alembic 配置
│
├── src/
│   └── app/                           # 主包（通用占位符，可重命名）
│       ├── __init__.py
│       ├── config.py                  # 全局配置（pydantic-settings）
│       │
│       ├── shared_kernel/             # 共享内核
│       │   ├── __init__.py
│       │   ├── domain/
│       │   │   ├── __init__.py
│       │   │   ├── entity.py               # 实体基类
│       │   │   ├── value_object.py         # 值对象基类
│       │   │   ├── aggregate_root.py       # 聚合根基类
│       │   │   ├── repository.py           # 仓储接口基类
│       │   │   └── exception.py            # 领域异常基类
│       │   ├── application/
│       │   │   ├── __init__.py
│       │   │   ├── command.py              # 命令基类
│       │   │   ├── query.py                # 查询基类
│       │   │   ├── command_handler.py      # 命令处理器基类
│       │   │   └── query_handler.py        # 查询处理器基类
│       │   └── infrastructure/
│       │       ├── __init__.py
│       │       ├── database.py             # SQLAlchemy 配置
│       │       ├── logging.py              # 日志配置
│       │       ├── messaging/              # 消息队列基础设施
│       │       │   └── __init__.py
│       │       └── sqlalchemy_repository.py  # 仓储基类实现
│       │
│       ├── modules/                   # 业务模块（子领域）目录
│       │   ├── __init__.py
│       │   │
│       │   └── .placeholder/           # 业务模块示例占位结构
│       │       ├── __init__.py
│       │       ├── domain/
│       │       │   ├── __init__.py
│       │       │   └── events/            # 领域事件定义
│       │       │       └── __init__.py
│       │       ├── application/
│       │       │   ├── __init__.py
│       │       │   ├── commands/
│       │       │   │   └── __init__.py
│       │       │   ├── queries/
│       │       │   │   └── __init__.py
│       │       │   └── event_handlers/    # 领域事件处理器
│       │       │       └── __init__.py
│       │       ├── infrastructure/
│       │       │   ├── __init__.py
│       │       │   └── models/
│       │       │       └── __init__.py
│       │       └── interfaces/             # 输入适配器（所有外部输入入口）
│       │           ├── __init__.py
│       │           ├── api/                 # HTTP API 路由
│       │           │   ├── __init__.py
│       │           │   ├── requests/
│       │           │   │   └── __init__.py
│       │           │   └── responses/
│       │           │       └── __init__.py
│       │           ├── events/              # 事件消费者（消息队列输入）
│       │           │   └── __init__.py
│       │           └── jobs/                # 定时任务（调度器输入）
│       │               └── __init__.py
│       │
│       └── interfaces/                # 全局接口入口
│           ├── __init__.py
│           ├── main.py                 # FastAPI 应用入口
│           ├── scheduler.py            # 全局定时任务调度器
│           ├── dependencies.py
│           ├── middleware.py
│           ├── exception_handler.py
│           └── response.py
│
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── shared_kernel/
│   │   └── modules/
│   │       └── <name>/
│   │           ├── domain/      # 领域测试
│   │           └── application/ # 应用层测试
│   └── integration/
│       └── ...
│
└── migrations/
    ├── __init__.py
    ├── env.py
    ├── script.py.mako
    └── versions/
```

## 4. 核心组件设计

### 4.1 统一响应格式

```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```

### 4.2 异常处理

- 领域异常 → 400/404
- 验证异常 → 422
- 系统异常 → 500

### 4.3 依赖方向

```
接口层 → 应用层 → 领域层 ← 基础设施层
```

---

## 5. 目录说明

### 5.1 根目录文件
- `pyproject.toml` - 项目元数据、依赖管理
- `environment.yml` - conda 环境配置
- `Dockerfile` - Docker 镜像构建文件
- `docker-compose.yml` - Docker Compose 编排配置
- `alembic.ini` - Alembic 数据库迁移配置
- `.env.example` - 环境变量示例

### 5.2 src/app/ - 主源码目录
- `config.py` - 全局配置（pydantic-settings）

### 5.3 src/app/shared_kernel/ - 共享内核
所有模块共用的基础代码。

**domain/ - 共享领域层**
- `entity.py` - 实体基类，定义实体的身份和相等性
- `value_object.py` - 值对象基类，不可变、通过属性值比较
- `aggregate_root.py` - 聚合根基类，业务一致性边界
- `repository.py` - 仓储接口基类，定义数据访问契约
- `exception.py` - 领域异常基类

**application/ - 共享应用层**
- `command.py` - 命令基类（改变状态的操作）
- `query.py` - 查询基类（读取数据的操作）
- `command_handler.py` - 命令处理器基类
- `query_handler.py` - 查询处理器基类

**infrastructure/ - 共享基础设施层**
- `database.py` - SQLAlchemy 数据库连接配置
- `logging.py` - 日志系统配置
- `messaging/` - 消息队列基础设施（连接、配置）
- `sqlalchemy_repository.py` - SQLAlchemy 仓储基类实现

### 5.4 src/app/modules/ - 业务模块目录
每个子领域作为一个独立模块，内部遵循同样的分层结构：
```
modules/[module_name]/
├── domain/              # 领域层
│   ├── events/          # 领域事件定义
│   └── ...
├── application/         # 应用层
│   ├── commands/        # 命令和处理器
│   ├── queries/         # 查询和处理器
│   └── event_handlers/  # 领域事件处理器
├── infrastructure/      # 基础设施层
│   └── models/          # 数据库模型
└── interfaces/          # 输入适配器（所有外部输入入口）
    ├── api/             # HTTP API 路由
    ├── events/          # 事件消费者（消息队列输入）
    └── jobs/            # 定时任务（调度器输入）
```

### 5.5 src/app/interfaces/ - 全局接口入口
- `main.py` - FastAPI 应用入口
- `scheduler.py` - 全局定时任务调度器
- `dependencies.py` - 全局依赖注入
- `middleware.py` - 中间件（CORS 等）
- `exception_handler.py` - 全局异常处理
- `response.py` - 统一响应格式定义

### 5.6 tests/ - 测试目录
- `conftest.py` - pytest 全局 fixture（如 mock UoW）
- `unit/` - 单元测试（纯领域/编排逻辑，mock 外部依赖）
  - `shared_kernel/` - 对应 `app/shared_kernel/`
  - `modules/<name>/` - 对应 `app/modules/<name>/`，**模块内按子目录**：`domain/`、`application/`（与源码一致）
- `integration/` - 集成测试（多层协作，如 aiosqlite 内存库）

### 5.7 migrations/ - 数据库迁移目录
- `env.py` - Alembic 环境配置
- `versions/` - 迁移版本文件

---

## 6. 编码基本原则

### 6.1 单一职责原则
- 每个文件只包含一个类/函数/概念
- 不要创建 `dtos.py`、`use_cases.py` 这种包含多个不相关内容的文件
- 例如：`create_user.py` 只定义创建用户命令，`create_user_handler.py` 只包含处理器

### 6.2 依赖规则（整洁架构）
- **领域层**：不依赖任何其他层，只包含纯业务逻辑
- **应用层**：依赖领域层，编排业务用例
- **基础设施层**：依赖领域层（实现仓储接口），不依赖应用层
- **接口层**：依赖应用层，处理 HTTP 请求/响应

### 6.3 领域层编码规则
- 实体使用 `dataclass`，`eq=False`，通过 ID 比较
- 值对象使用 `dataclass(frozen=True, eq=True)`，不可变
- 所有业务规则都在领域层实现
- 领域异常继承自 `DomainException`
- 仓储只定义接口，不包含实现

### 6.4 应用层编码规则
- 命令和查询使用 `dataclass(frozen=True)`
- 每个命令/查询对应一个独立的处理器
- DTO 放在相关的命令/查询旁边，高内聚
- 应用层只编排，不包含业务规则

### 6.5 基础设施层编码规则
- 仓储实现继承自 `SqlAlchemyRepository`
- 实现 `_to_entity()` 和 `_to_model()` 方法进行转换
- 数据库模型放在 `models/` 目录下

### 6.6 接口层编码规则（输入适配器）
- **HTTP API**：放在 `interfaces/api/` 目录
  - 请求模型放在 `api/requests/`
  - 响应模型放在 `api/responses/`
  - 路由使用 FastAPI 的 `APIRouter`
- **事件消费者**：放在 `interfaces/events/` 目录
  - 从消息队列消费事件
  - 调用应用层用例
- **定时任务**：放在 `interfaces/jobs/` 目录
  - 被调度器触发
  - 调用应用层用例
- 统一使用 `ApiResponse` 包装 HTTP 响应
- 异常在 `exception_handler.py` 统一处理

### 6.7 测试规则
- 单元测试只测试领域逻辑，不依赖外部
- 集成测试测试多层协作，使用测试数据库
- 测试文件命名：`test_*.py`

---

## 7. 部署架构

Docker Compose 管理两个服务：
- `web`：FastAPI 应用
- `db`：PostgreSQL 数据库
