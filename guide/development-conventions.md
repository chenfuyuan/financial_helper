# 代码开发规范

本文档为 AI 与开发者在**进行代码开发时**使用的规范。非开发对话无需加载。编辑 src 时代入 **`guide/architecture.md`**，编辑 tests 时代入 **`guide/testing.md`**。

## 架构与约束

分层：`interfaces → application → domain ← infrastructure`。分层依赖、Domain/Application/Infrastructure/Interfaces 编码规则、单一职责与事务边界等见 **`guide/architecture.md`**。

## 目录结构

```
src/app/
├── shared_kernel/     # 共用基类（domain / application / infrastructure）
├── modules/<name>/    # 业务模块
│   ├── domain/        # entities/, gateways/, repositories/; exceptions.py 可选
│   ├── application/   # commands/, queries/
│   ├── infrastructure/# gateways/（含 mappers/）, repositories/（含 mappers/）, models/
│   └── interfaces/    # api/, dependencies.py（模块专属依赖）
└── interfaces/        # main.py, dependencies.py（跨模块共享依赖）
```

- **domain**：entities 一文件一概念；gateways 为外部数据接口，repositories 为持久化接口。
- **application**：Handler 模块路径须含 `.commands.` 或 `.queries.`。
- **infrastructure**：gateways/mappers 做「API 响应 → 领域模型」；repositories/mappers 做「领域模型 → 持久化」。新模块与 data_engineering 对齐。

## 依赖注入规范

- **跨模块共享依赖**（Database、Mediator、UoW 等）：仅放在 `app/interfaces/dependencies.py`，由 `main.py` 的 lifespan 挂到 `app.state`，供全局使用。
- **模块内专属依赖**（本模块的 Repository、Gateway、Handler 的组装）：放在各模块自己的 `modules/<name>/interfaces/dependencies.py` 中，通过 `Depends(get_uow)` 等从全局获取共享依赖后，构造并返回本模块的 Handler 或所需实例。
- **Router**：只通过 `Depends(...)` 注入全局或模块提供的依赖，不在路由函数内手写 `new` Gateway/Repository/Handler。

## 命令

```bash
make dev   make test   make lint   make format   make type-check
make ci    # 提交前必跑（lint + format check + mypy + architecture-check + pytest）
make architecture-check   make migrate   make migrate-create msg="描述"
make new-module name=<模块名>   make docker-up
```

## 数据库设计规范

- **基础字段**（必含）：id、created_at、updated_at、version。业务表在此基础上增加业务列；模型与迁移均显式包含上述四类。
- **字段顺序**：`id` 最前，业务字段居中，`created_at` / `updated_at` / `version` 最后。模型属性顺序与 Alembic `create_table` / `add_column` 列顺序一致。

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
