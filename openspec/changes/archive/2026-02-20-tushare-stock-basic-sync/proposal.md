# Proposal: TuShare 股票基础信息同步

## Why

系统需要一份本地可复用的 A 股股票基础信息表，作为后续分析与研究的基础数据源；目前缺少从外部数据源拉取并持久化该数据的能力。通过从 TuShare `stock_basic` 接口获取数据并在 PostgreSQL 中维护，可先实现「一次性/按需同步」，后续如需每日定时同步，只需在调度层复用同一用例入口即可。

## What Changes

- **data_engineering 模块**：在 `app/modules/data_engineering/` 下按 DDD 分层新增股票基础信息相关代码。
- **领域层**：引入领域实体 `StockBasic`（含第三方代码、来源、基本信息、上市状态等）、外部数据网关接口 `StockGateway`、本地持久化接口 `StockBasicRepository`；逻辑唯一键为 `(source, third_code)`，便于未来支持多数据源。
- **应用层**：新增命令 `SyncStockBasic` 与 Handler `SyncStockBasicHandler`，编排「从网关拉取 → 仓储批量 upsert → 提交事务」，幂等、不暴露 TuShare 细节。
- **基础设施层**：实现 `TuShareStockGateway`（调用 TuShare、将响应映射为领域对象）、`SqlAlchemyStockBasicRepository`（PostgreSQL 表 + `ON CONFLICT` upsert）、对应 SQLAlchemy 模型与迁移。
- **接口层**：暴露 `POST /data-engineering/stock-basic/sync`，通过 Mediator 发送 `SyncStockBasic`，返回同步条数/耗时或统一错误响应。
- **错误与幂等**：TuShare 失败时统一异常、不提交事务；单条解析失败可记录日志并跳过；以 `(source, third_code)` upsert 保证同一天多次调用结果一致。

## Capabilities

### New Capabilities

- `stock-basic-sync`：从 TuShare 拉取 A 股股票基础信息并写入本地 PostgreSQL，支持通过 HTTP 按需触发；领域不依赖 TuShare 具体格式，网关与仓储可替换扩展。

### Modified Capabilities

- （无：当前 `openspec/specs/` 下无既有能力，不涉及对现有 spec 的需求变更。）

## Impact

- **代码**：`app/modules/data_engineering/` 下新增 domain/application/infrastructure/interfaces 若干文件。
- **数据库**：新增股票基础信息表及 Alembic 迁移；表结构遵循项目数据库设计规范（基础字段：id、created_at、updated_at、version）。
- **依赖**：引入 TuShare 客户端（或现有数据工程依赖中已有）。
- **API**：新增管理端同步接口 `POST /data-engineering/stock-basic/sync`，供手工触发或后续调度/CLI 复用同一命令。
