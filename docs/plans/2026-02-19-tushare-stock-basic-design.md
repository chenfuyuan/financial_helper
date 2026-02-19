## TuShare Stock Basic 同步设计（data-engineering 模块）

### 1. 背景与目标

- 从 TuShare `stock_basic` 接口获取 A 股股票基础信息。
- 在本地 PostgreSQL 中维护一份可复用的股票基础信息表，作为后续分析与研究的基础数据源。
- 目前阶段：仅实现「一次性/按需同步」能力，通过 HTTP 接口触发；后续如需每日 18:00 定时任务，再在调度层以同一用例为入口扩展。

### 2. 模块与分层设计

整体仍然遵循项目的 DDD 分层约定：

- `domain`：领域实体、网关接口、仓储接口，不依赖外部实现。
- `application`：用例（命令 + Handler），编排网关与仓储，不写具体技术细节。
- `infrastructure`：SQLAlchemy 模型、仓储实现、TuShare 网关实现。
- `interfaces`：FastAPI 路由，对外暴露同步入口。

#### 2.1 模块目录（data_engineering）

在 `app/modules/data_engineering/` 下新增：

- `domain/`
  - `stock_basic.py`：领域实体 `StockBasic`、状态枚举等。
  - `stock_gateway.py`：外部股票数据网关接口 `StockGateway`。
  - `stock_basic_repository.py`：本地持久化接口 `StockBasicRepository`。
- `application/`
  - `commands/sync_stock_basic.py`：命令对象 `SyncStockBasic`。
  - `commands/sync_stock_basic_handler.py`：命令 Handler `SyncStockBasicHandler`。
- `infrastructure/`
  - `models/stock_basic_model.py`：PostgreSQL 表的 SQLAlchemy 模型。
  - `tushare_stock_gateway.py`：TuShare 实现 `TuShareStockGateway`，实现 `StockGateway`。
  - `sqlalchemy_stock_basic_repository.py`：实现 `StockBasicRepository`。
- `interfaces/api/`
  - `stock_basic_router.py`：FastAPI 路由，提供同步触发接口等。

> 目前不引入 foundation 层的调度能力，只保留「通过接口/命令显式触发同步」的能力，将来如需每日 18:00 定时任务，只需要在调度层调用同一个 `SyncStockBasic` 命令。

### 3. 领域层设计

#### 3.1 领域实体 `StockBasic`

领域内不直接使用 TuShare 专属字段名（如 `ts_code`），而是抽象为通用的「第三方代码 + 来源」：

- 标识与来源
  - `id`: 内部主键（数据库用，领域中可以弱化）。
  - `third_code`: `str` —— 外部数据源中的股票代码（如 TuShare 的 `ts_code`）。
  - `source`: `str` 或枚举 `DataSource` —— 数据来源（例如 `"TUSHARE"`）。
- 基本信息
  - `symbol`: `str`
  - `name`: `str`
  - `market`: `str`
  - `area`: `str | None`
  - `industry`: `str | None`
- 生命周期
  - `list_date`: `date`
  - `status`: `StockStatus` 枚举：`LISTED` / `DELISTED` / `SUSPENDED`
- 元数据（可选）
  - `created_at`: `datetime`
  - `updated_at`: `datetime`

逻辑唯一键建议使用 `(source, third_code)`，以便未来支持多个外部数据源。

#### 3.2 外部数据网关接口 `StockGateway`

定义统一的外部股票数据访问接口：

- `fetch_stock_basic() -> list[StockBasic]`

约定：

- 接口返回的已经是领域对象 `StockBasic` 列表，调用方（application 层）不关心 TuShare 具体字段格式。
- 不暴露任何 TuShare 专属 DTO 类型或字段名，保证未来可以替换数据源。

#### 3.3 仓储接口 `StockBasicRepository`

抽象本地 PostgreSQL 持久化行为，典型方法：

- `upsert_many(stocks: list[StockBasic])`：批量 upsert。
- （可选）`list_all()`、`get_by_third_code(source, third_code)` 等查询方法，根据后续需求扩展。

upsert 语义：

- 以 `(source, third_code)` 为逻辑唯一键执行插入/更新。
- 已存在则更新基本信息与状态；不存在则插入新记录。

### 4. application 层：同步用例

#### 4.1 命令对象 `SyncStockBasic`

- 一个简单的命令对象，用来表达「执行一次 stock_basic 同步」这一用例。
- 初期可以不携带参数，将来可扩展：
  - 只同步特定 `market`。
  - 只同步特定 `source`。

#### 4.2 Handler `SyncStockBasicHandler`

依赖注入：

- `StockGateway`：运行时注入为 `TuShareStockGateway`。
- `StockBasicRepository`。
- `UnitOfWork`：来自 shared_kernel。

执行流程：

1. 调用 `gateway.fetch_stock_basic()` 获取 `list[StockBasic]`。
2. 调用 `repository.upsert_many(stocks)` 将数据写入 PostgreSQL。
3. 提交 `UnitOfWork`。
4. 记录必要的日志（同步条数、耗时、来源）。

用例特性：

- 幂等：同一天多次调用，最终数据库状态一致。
- 把 TuShare 细节完全封装在 `StockGateway` 实现中，application 层只面向领域接口。

### 5. infrastructure 层实现

#### 5.1 TuShare 网关实现 `TuShareStockGateway`

职责：

- 调用 TuShare 的 `stock_basic` 接口。
- 将 TuShare 返回的数据（DataFrame / dict 列表）转换为 `list[StockBasic]`。

字段映射约定：

- TuShare `ts_code` → 领域 `third_code`。
- 固定 `source = "TUSHARE"`（或 `DataSource.TUSHARE`）。
- 其他字段：
  - `symbol` → `symbol`
  - `name` → `name`
  - `market` → `market`
  - `area` → `area`
  - `industry` → `industry`
  - `list_date`（`YYYYMMDD` 字符串）→ `date`。
  - `list_status`：
    - `L` → `StockStatus.LISTED`
    - `D` → `StockStatus.DELISTED`
    - `P` → `StockStatus.SUSPENDED`

错误与脏数据处理：

- 网络错误 / 授权失败 / 限流：
  - 捕获底层异常，转换为统一的 `ExternalStockServiceError`（或类似领域/应用层异常）。
  - 由 Handler 决定是否重试或直接失败。
- 单条数据解析错误（如日期非法）：
  - 可先采用「记录警告日志 + 跳过该条」策略。
  - 如果解析失败条数过多，可以考虑后续扩展为「整体失败」模式。

#### 5.2 仓储实现 `SqlAlchemyStockBasicRepository`

SQLAlchemy 模型 `StockBasicModel`：

- 字段对应 `StockBasic` 领域实体：
  - `id`（PK，自增）。
  - `source` + `third_code`（唯一索引）。
  - `symbol`、`name`、`market`、`area`、`industry` 等。
  - `list_date`、`status`、`created_at`、`updated_at`。

`upsert_many` 实现要点：

- 使用数据库层面的 upsert 能力（如 `ON CONFLICT (source, third_code) DO UPDATE`）。
- 只更新需要的字段，保持 `created_at` 不变，`updated_at` 刷新。
- 在同一事务里完成一批数据的 upsert，交由 `UnitOfWork` 管理提交/回滚。

### 6. interfaces 层：HTTP 同步接口

在 `interfaces/api/stock_basic_router.py` 中：

- 暴露管理端同步接口：
  - `POST /data-engineering/stock-basic/sync`
  - 行为：通过 Mediator/CommandBus 发送 `SyncStockBasic` 命令，等待执行完成后返回结果。
- 响应内容：
  - 成功时：返回同步条数、耗时等基础信息。
  - 失败时：统一异常处理中间件转换为标准错误响应（如 500 + 错误信息）。

说明：

- 该接口既可用于「手工触发一次全量同步」，也为后续调度系统（如定时任务）提供 HTTP/内部调用入口。
- 将来如果引入 job runner/CLI，可以直接在 job 中复用同一个命令/用例，而不是重复编写同步逻辑。

### 7. 错误处理与幂等性

错误处理：

- TuShare 调用失败（网络、鉴权、限流）：
  - `TuShareStockGateway` 抛出统一异常，Handler 记录错误日志并终止同步，不提交事务。
- 数据解析错误：
  - 单条记录解析失败 → 日志记录 + 跳过该条。
  - 如果未来业务需要更严格的策略，可在网关中增加统计与阈值控制。
- 数据库异常：
  - `upsert_many` 或事务提交失败 → 抛出异常，由上层统一异常处理中间件处理。

幂等性：

- 用 `(source, third_code)` 作为 upsert 唯一键，同一天、多次调用 `SyncStockBasic`，最终数据库中的行集与字段值一致。
- 退市/暂停股票通过 `status` 字段维护，不进行物理删除，保留历史信息。

### 8. 测试策略

#### 8.1 domain 层测试

- 为 `StockBasic` 等实体编写单元测试，验证：
  - 字段约束（如状态枚举）。
  - 未来若有领域方法（如状态切换），验证其业务规则。
- 为 `StockGateway` / `StockBasicRepository` 接口定义预期行为契约（例如通过伪实现或接口文档测试）。

#### 8.2 application 层测试

- 对 `SyncStockBasicHandler` 编写单元测试，使用 fake/mock：
  - 使用 fake `StockGateway` 返回构造好的 `StockBasic` 集合。
  - 使用 fake `StockBasicRepository` 记录入参，验证 `upsert_many` 是否按预期被调用。
  - 验证在异常情况下（网关抛错、仓储抛错）不提交事务，并向上抛出异常。

#### 8.3 infrastructure 层测试

- `TuShareStockGateway`：
  - 使用 TuShare 响应的假数据（DataFrame/dict 列表），测试字段映射和状态枚举转换。
  - 覆盖日期解析、缺失字段/非法数据的日志与跳过策略。
- `SqlAlchemyStockBasicRepository`：
  - 使用测试数据库（如内存 SQLite 或测试用 PostgreSQL）：
    - 测试 `upsert_many` 的插入/更新行为。
    - 验证 `(source, third_code)` 唯一约束和幂等性。

#### 8.4 接口测试

- 针对 `POST /data-engineering/stock-basic/sync`：
  - 使用 FastAPI 测试客户端，mock 掉真实 TuShare 网关。
  - 验证：
    - 成功时返回的状态码和响应体格式。
    - 失败时的错误响应结构。

