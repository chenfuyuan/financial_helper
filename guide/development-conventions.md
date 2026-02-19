# 代码开发规范

本文档为 AI 与开发者在**进行代码开发时**使用的规范。非开发对话无需加载。编辑 src 时代入 **`guide/architecture.md`**，编辑 tests 时代入 **`guide/testing.md`**。

## 核心原则

### 1. 架构优先
- **严格分层**：`interfaces → application → domain ← infrastructure`
- **依赖方向**：外层依赖内层，内层不依赖外层
- **领域纯净**：domain 层不 import 任何其他层

### 2. DDD 建模规范
- **聚合根**：继承 `AggregateRoot[ID]`，拥有独立 Repository
- **实体**：继承 `Entity[ID]`，仅包含业务属性，不含基础设施字段（created_at/updated_at/version）
- **值对象**：复合值对象继承 `ValueObject`（`@dataclass(frozen=True)` + `_validate()`）；枚举类型的值对象允许使用 `StrEnum`/`IntEnum`
- **领域事件**：继承 `DomainEvent`，由聚合根发布
- **领域异常**：继承 `DomainException`，不直接继承 `Exception`

### 3. 事务边界
- **Application 层控制事务**：Handler 接收 UoW，在 `handle()` 内 `await uow.commit()`
- **Interfaces 层不控制事务**：Router 只做 HTTP 编排，不调用 `uow.commit()`

## 目录结构

```
src/app/
├── shared_kernel/                    # 跨模块共享构建块
│   ├── domain/                       # 领域基类（aggregate_root, entity, value_object, domain_event, exception, repository, unit_of_work）
│   ├── application/                  # 应用层基类（command, command_handler, query, query_handler, mediator, event_bus, dto）
│   └── infrastructure/               # 基础设施基类（database, sqlalchemy_repository, sqlalchemy_unit_of_work, logging, cache, message_bus, scheduler）
│
├── modules/<module_name>/             # 业务模块
│   ├── domain/                       # 领域层
│   │   ├── entities/                 # 聚合根/实体（一文件一概念）
│   │   ├── value_objects/            # 值对象
│   │   ├── gateways/                 # 外部服务接口
│   │   ├── repositories/             # 持久化接口
│   │   ├── services/                 # 领域服务
│   │   ├── events/                   # 领域事件定义
│   │   └── exceptions.py             # 领域异常
│   ├── application/                  # 应用层
│   │   ├── commands/                 # 命令与处理器（Handler 路径须含 `.commands.`）
│   │   ├── queries/                  # 查询与处理器（Handler 路径须含 `.queries.`）
│   │   └── events/                   # 事件处理器
│   ├── infrastructure/               # 基础设施层
│   │   ├── models/                   # ORM 模型
│   │   ├── gateways/                 # 外部服务实现
│   │   │   └── mappers/              # 数据映射（API 响应 → 领域模型）
│   │   ├── repositories/             # 仓储实现
│   │   │   └── mappers/              # 持久化映射（领域模型 → 持久化）
│   │   ├── cache/                    # 缓存实现
│   │   └── tasks/                    # 异步任务
│   └── interfaces/                   # 接口层
│       ├── api/                      # HTTP 路由
│       ├── consumers/                # MQ 消费者
│       ├── schedulers/               # 定时任务
│       └── dependencies.py           # 模块内 DI
│
└── interfaces/                        # 全局接口层
    ├── main.py                       # FastAPI 应用
    ├── module_registry.py            # 模块注册器（新增模块在此追加 Router）
    ├── dependencies.py               # 跨模块依赖
    ├── exception_handler.py          # 异常处理
    ├── middleware.py                 # 中间件
    └── response.py                   # 响应模型
```

## 依赖注入规范

- **跨模块共享依赖**（Database、Mediator、UoW 等）：仅放在 `app/interfaces/dependencies.py`，由 `main.py` 的 lifespan 挂到 `app.state`，供全局使用。
- **模块内专属依赖**（本模块的 Repository、Gateway、Handler 的组装）：放在各模块自己的 `modules/<name>/interfaces/dependencies.py` 中，通过 `Depends(get_uow)` 等从全局获取共享依赖后，构造并返回本模块的 Handler 或所需实例。
- **Router**：只通过 `Depends(...)` 注入全局或模块提供的依赖，不在路由函数内手写 `new` Gateway/Repository/Handler。

## 模块注册规范

- **新增模块**时，在 `app/interfaces/module_registry.py` 的 `_collect_module_routers()` 中追加 Router 与前缀，`main.py` 无需修改。
- **日志配置**通过参数注入（`configure_logging(log_level=..., app_env=...)`），`shared_kernel/infrastructure/logging.py` 不直接依赖 `app.config`。

## 仓储接口规范

- 通用 CRUD 场景可继承 `shared_kernel.domain.repository.Repository[AR, ID]`。
- 批量操作等特殊场景允许模块仓储接口独立定义 ABC（如 `StockBasicRepository.upsert_many`），不强制继承通用基类。
- 基础设施实现可同时继承 `SqlAlchemyRepository` 和模块仓储接口，按需覆盖方法。

## 数据库设计规范

- **ORM 模型字段**：id 最前，业务字段居中，审计字段（created_at/updated_at/version）最后。
- **领域实体字段**：仅包含业务属性，不包含审计字段（created_at/updated_at/version），这些由 ORM 模型和数据库维护。
- **字段顺序**：模型属性顺序与 Alembic `create_table` / `add_column` 列顺序一致。

## 架构守护

- import-linter 检查层内依赖；`tests/architecture/` 的 pytest 检查 Handler 位置与 domain 继承。
- 违反会导致 `make ci` 失败。新模块用标准四层目录即可；若用枚举 container，在 `pyproject.toml` 的 import-linter `containers` 中追加 `app.modules.<name>`。

## 日志规范

- **结构化**：使用键值/字段形式，便于检索、聚合与告警；不依赖消息字符串拼接变量。
- **级别**：debug 仅排查用，info 关键业务节点，warning 可恢复异常或降级，error 须带足够上下文（如堆栈或请求标识）以便排查。
- **安全与性能**：不记录密码、令牌、完整请求体等敏感信息；不在循环或高频路径打 info/debug，避免日志膨胀与性能问题。

## 注释与文档字符串规范

- **公开 API**：模块与对外暴露的类、方法须有文档说明（中文），简述职责、行为与关键约束；实现细节可由命名表达的不赘述。
- **行内注释**：只解释「为什么」、业务/技术约束或非显然假设，不复述代码在做什么。
- **禁止**：无信息量注释、过期注释；复杂逻辑优先用命名与拆函数表达，不依赖长段注释。

## 测试与验证

测试目录与编写规则见 **`guide/testing.md`**。运行：`python -m pytest tests/ -v`。提交前执行 **`make ci`**。