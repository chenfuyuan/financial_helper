# Design: TuShare 股票基础信息同步

实现 spec「stock-basic-sync」：从 TuShare 拉取 A 股股票基础信息，以 (source, third_code) 为唯一键幂等写入 PostgreSQL，通过 HTTP 按需触发；整批解析成功才落库，任一条解析失败则整次同步失败。

## Context

- **现状**：项目已有 DDD 分层（domain / application / infrastructure / interfaces）、shared_kernel（UnitOfWork、Mediator）、示例模块 example；尚无 data_engineering 模块，也无股票基础数据表。
- **约束**：遵循 CLAUDE.md 与 `docs/plans/financial-helper/` 的架构约定；domain 零外部依赖；事务由 UnitOfWork 统一提交；import-linter 与 architecture 测试需通过。
- **相关方**：后续分析与研究模块依赖本地股票基础表；调度/CLI 可复用同一同步命令。

## Goals / Non-Goals

**Goals:**

- 在 `app/modules/data_engineering/` 下实现 stock_basic 同步能力，满足 [specs/stock-basic-sync/spec.md](./specs/stock-basic-sync/spec.md) 全部需求。
- 领域不依赖 TuShare 或 PostgreSQL 实现细节；网关与仓储接口可替换（如换数据源、换库）。
- 一次同步 = 一次网关拉取的一批数据，全量解析成功才 upsert，任一条解析失败则整次失败、不提交。
- 暴露 `POST /data-engineering/stock-basic/sync`，成功返回条数（及可选耗时），失败走统一异常处理。

**Non-Goals:**

- 不实现定时调度（如每日 18:00）；仅提供按需触发的入口，调度层后续可复用同一命令。
- 不实现按 market/source 过滤的增量同步参数（可后续在命令上扩展）。
- 不引入除 TuShare 客户端、现有 DB/Mediator 以外的新的基础设施组件。

## Decisions

### 1. 模块与目录结构（data_engineering）

在 `app/modules/data_engineering/` 下按项目约定分四层，与现有 example 模块一致：

- **domain/**：`stock_basic.py`（实体 + 枚举）、`stock_gateway.py`（网关接口）、`stock_basic_repository.py`（仓储接口）。
- **application/commands/**：`sync_stock_basic.py`（命令）、`sync_stock_basic_handler.py`（Handler）。
- **infrastructure/**：`models/stock_basic_model.py`、`tushare_stock_gateway.py`、`sqlalchemy_stock_basic_repository.py`。
- **interfaces/api/**：`stock_basic_router.py`，挂到 `/data-engineering/stock-basic`。

**理由**：与 02-dependencies、模块文档一致，便于架构守护与后续扩展。  
**备选**：把网关放在 shared_kernel — 拒绝，因网关是「外部股票数据」的端口，属于 data_engineering 限界上下文。

### 2. 领域唯一键与实体字段

- 逻辑唯一键：`(source, third_code)`。持久化与 upsert 均以此为准。
- 遵循项目**数据库设计规范**（CLAUDE.md）：持久化对象必须包含基础字段 **id、created_at、updated_at、version**。
- 实体 `StockBasic` 字段：
  - 基础字段：`id`、`created_at`、`updated_at`、`version`（与规范一致）。
  - 业务字段：`source`、`third_code`、`symbol`、`name`、`market`、`area`、`industry`、`list_date`、`status`（枚举 LISTED/DELISTED/SUSPENDED）。`source` 用 str 或枚举 `DataSource` 均可，便于多数据源扩展。

**理由**：与 spec「以 (source, third_code) 为唯一键幂等持久化」及「持久化记录包含基础字段与必要业务字段」一致；与项目规范统一。  
**备选**：仅用 `ts_code` — 拒绝，无法区分多数据源。

### 3. 网关契约：全量解析成功或抛错（无部分成功）

- `StockGateway.fetch_stock_basic() -> list[StockBasic]`：要么返回「整批已解析好的」领域对象列表，要么抛出异常（网络/鉴权/限流/解析失败）。
- TuShare 实现中：先拉取原始数据，再逐条解析为 `StockBasic`；任一条解析失败（日期非法、必填缺失等）即抛出统一异常（如 `ExternalStockServiceError` 或领域层解析异常），不返回部分结果。

**理由**：满足 spec「单条解析失败则整次同步失败」「不提交任何变更」。  
**备选**：网关返回 (success_list, error_list) — 拒绝，spec 要求整批成功才落库，Handler 层不应处理部分成功。

### 4. Handler 与事务边界

- Handler 依赖：`StockGateway`、`StockBasicRepository`、`UnitOfWork`（shared_kernel）。
- 流程：在 UnitOfWork 上下文内调用 `gateway.fetch_stock_basic()` → `repository.upsert_many(stocks)` → `uow.commit()`；任一步异常则不再 commit，异常上抛，由接口层/统一异常处理返回 5xx 或统一错误格式。
- 不在 Handler 内 catch 后做部分提交；网关或仓储抛错即视为同步失败。

**理由**：与 spec「外部源失败/解析失败时不提交」一致；事务边界清晰。  
**备选**：在 Handler 内重试网关 — 本设计不采纳，后续若需要可在应用层加重试策略。

### 5. 仓储 upsert 与模型

- `StockBasicRepository.upsert_many(stocks: list[StockBasic])`：在单次事务内完成整批写入。
- 数据库：唯一约束 `UNIQUE(source, third_code)`，使用 `ON CONFLICT (source, third_code) DO UPDATE` 更新业务字段；**基础字段**按规范处理：`created_at` 不变，`updated_at` 刷新为当前时间，`version` 递增（乐观锁）；插入时 `version` 赋初值（如 0 或 1）。
- SQLAlchemy 模型：表名 `stock_basic`，包含规范要求的**基础字段**（id、created_at、updated_at、version）及业务字段，与领域实体对齐。

**理由**：满足 spec 幂等与「首次插入/再次更新/多次结果一致」；符合 CLAUDE.md 数据库设计规范。  
**备选**：先 delete 再 insert — 拒绝，会丢失 created_at 且非幂等语义。

### 6. HTTP 接口与依赖注入

- 路由：`POST /data-engineering/stock-basic/sync`，无请求体或空 body。
- 行为：通过 Mediator 发送 `SyncStockBasic` 命令；Handler 需注入 `StockGateway`（TuShare 实现）、`StockBasicRepository`（从当前请求的 UnitOfWork 取得 session 构造）、UnitOfWork 由 Mediator/路由侧保证在同一请求内一致（参考 example 中 command 与 uow 的配合方式）。
- 成功：2xx，响应体至少含 `synced_count`（本次同步条数），可选 `duration_ms`。
- 失败：不捕获业务/网关/仓储异常，由 FastAPI 统一异常处理中间件转换为标准错误响应（如 500 + message）。

**理由**：与 spec「同步可由 HTTP 触发」「成功时返回同步结果摘要」「失败时返回错误」一致。  
**备选**：路由内直接 new Handler + gateway + repo — 可用，但若项目已统一用 Mediator 注册 Command/Handler，建议走 Mediator 以保持风格一致。

### 7. TuShare 字段映射与枚举

- `ts_code` → `third_code`；`source` 固定为 `"TUSHARE"` 或 `DataSource.TUSHARE`。
- `symbol`、`name`、`market`、`area`、`industry` 直映射；`list_date` 为 YYYYMMDD 字符串转为 `date`；`list_status`：`L`→LISTED，`D`→DELISTED，`P`→SUSPENDED。
- 解析时对必填或格式做校验，失败即抛异常，不返回部分列表。

**理由**：与既有设计文档一致，且满足 spec 全量解析成功或失败。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| TuShare 限流/不稳定 | 网关层统一异常类型；Handler 不提交；必要时后续在应用层加重试/退避。 |
| 单次全量数据量大导致内存/超时 | 当前为按需全量；若后续数据量显著增大，可考虑分页拉取或流式解析，并在网关接口上扩展。 |
| 表结构后续变更 | 通过 Alembic 管理迁移；设计上仅新增表、不修改其他模块表。 |
| 网关/仓储实现与领域接口不一致 | 单测 + 集成测：fake 网关与内存库验证 Handler；网关单测用假 TuShare 响应验证映射与「解析失败即抛」。 |

## Migration Plan

1. **实现顺序建议**：domain（实体、网关接口、仓储接口）→ infrastructure（模型 + 迁移、TuShare 网关、仓储实现）→ application（命令 + Handler）→ interfaces（路由、注册依赖与 Mediator）。
2. **数据库**：新增 Alembic 迁移，创建 `stock_basic` 表；表结构含规范要求的基础字段（id、created_at、updated_at、version）及业务字段，并设 `UNIQUE(source, third_code)`。无存量数据依赖，无需数据迁移脚本。
3. **回滚**：若需回滚，执行 `alembic downgrade` 删除该表；接口下线可通过路由注释或特性开关控制。
4. **部署**：先执行迁移，再部署新代码；接口可配合权限/内网限制，避免误触。

## Open Questions

- **无**：当前 spec 与设计文档已对齐；若后续增加「按 market 过滤」等参数，需在命令与 spec 中同步扩展。
