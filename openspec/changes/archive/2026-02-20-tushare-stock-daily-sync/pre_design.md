# 预设计文档：Tushare 股票日线数据同步

## 1. 总体架构

遵循现有 `data_engineering` 模块的 DDD + 整洁架构模式：
- **Domain Layer**: `StockDaily` 实体、`StockDailyGateway` 接口（独立于 StockGateway，SRP）、`StockDailyRepository` 接口、`StockDailySyncFailure` 实体、`StockDailySyncFailureRepository` 接口
- **Application Layer**: 三个 Command + Handler（历史同步、增量同步、重试失败记录）
- **Infrastructure Layer**: `TuShareStockDailyGateway` 实现、`SqlAlchemyStockDailyRepository`、`SqlAlchemyStockDailySyncFailureRepository`、数据库模型、Gateway Mapper、Persistence Mapper
- **Interface Layer**: HTTP 路由

## 2. 数据模型设计

### StockDaily 实体（领域层）

合并 daily、adj_factor、daily_basic 三个接口字段。遵循项目规范：**仅含业务属性，不含审计字段**（`created_at`/`updated_at`/`version` 由 ORM 模型和数据库维护）：

- 标识字段：`id: int | None`、`source: DataSource`、`third_code: str`、`trade_date: date`
- daily 字段（`Decimal`）：`open`、`high`、`low`、`close`、`pre_close`、`change`、`pct_chg`、`vol`、`amount`
- adj_factor 字段：`adj_factor: Decimal`
- daily_basic 字段（`Decimal | None`，新股/停牌股部分指标可能缺失）：`turnover_rate`、`turnover_rate_f`、`volume_ratio`、`pe`、`pe_ttm`、`pb`、`ps`、`ps_ttm`、`dv_ratio`、`dv_ttm`、`total_share`、`float_share`、`free_share`、`total_mv`、`circ_mv`
- 唯一约束：`(source, third_code, trade_date)`

### StockDailySyncFailure 实体（领域层）

- 标识字段：`id: int | None`、`source: DataSource`、`third_code: str`
- 同步范围：`start_date: date`、`end_date: date`（重试时需要知道失败的日期范围）
- 失败信息：`error_message: str`、`failed_at: datetime`、`retry_count: int`、`resolved: bool`

## 3. 网关接口设计

### StockDailyGateway（独立抽象接口）

按 SRP 原则，日线数据网关为独立接口，不扩展 `StockGateway`。参数使用领域类型 `date`，不暴露 TuShare 的字符串格式：

```python
class StockDailyGateway(ABC):
    """从外部数据源拉取股票日线行情。内部封装 daily、adj_factor、daily_basic 的调用与组装。"""

    @abstractmethod
    async def fetch_stock_daily(
        self, ts_code: str, start_date: date, end_date: date
    ) -> list[StockDaily]:
        """获取单只股票指定日期范围的完整日线数据。"""

    @abstractmethod
    async def fetch_daily_all_by_date(self, trade_date: date) -> list[StockDaily]:
        """获取某一交易日所有股票的完整日线数据。内部处理 TuShare 分页（单次 ≤5000 条）。"""
```

### 封装逻辑说明（TuShareStockDailyGateway 实现）

- `fetch_stock_daily`：内部依次调用 TuShare `daily`、`adj_factor`、`daily_basic`（均按 `ts_code` + 日期范围），按 `trade_date` 合并组装
- `fetch_daily_all_by_date`：按 `trade_date` 调用三个接口，各接口内部处理分页（A 股 5000+ 只股票，TuShare 单次最多约 5000 条）
- 任一接口失败或数据解析失败则整体抛 `ExternalStockServiceError`
- daily_basic 中新股/停牌股部分字段可能为 None，Mapper 需容许
- **限流**：Gateway 实例内维护 Token Bucket（容量 200，每分钟补充 200），每次 API 调用前 acquire；相比固定 `asyncio.sleep` 更精确且不浪费等待时间

## 4. 仓储接口设计

### StockDailyRepository

```python
class StockDailyRepository(ABC):
    @abstractmethod
    async def upsert_many(self, records: list[StockDaily]) -> None:
        """以 (source, third_code, trade_date) 为唯一键批量 upsert。不 commit。"""

    @abstractmethod
    async def get_latest_trade_date(self, source: DataSource, third_code: str) -> date | None:
        """查询某只股票本地已有的最新交易日期，用于断点续传。无记录返回 None。"""
```

### StockDailySyncFailureRepository

```python
class StockDailySyncFailureRepository(ABC):
    @abstractmethod
    async def save(self, failure: StockDailySyncFailure) -> None:
        """保存失败记录（新增或更新 retry_count）。"""

    @abstractmethod
    async def find_unresolved(self, max_retries: int = 3) -> list[StockDailySyncFailure]:
        """查询未解决且 retry_count < max_retries 的失败记录。"""

    @abstractmethod
    async def mark_resolved(self, failure_id: int) -> None:
        """标记为已解决。"""
```

## 5. 应用层设计

### 三个 Command

1. **SyncStockDailyHistory** — 历史数据同步
   - 参数：`ts_codes: list[str] | None`（不传则同步所有股票）
   - 依赖：`StockBasicRepository`（获取股票列表及上市日期）、`StockDailyGateway`、`StockDailyRepository`、`StockDailySyncFailureRepository`、`UnitOfWork`
   - 流程：
     1. 若未指定 ts_codes，从 `StockBasicRepository` 查询全部已上市股票
     2. 遍历每只股票：
        a. 查本地该股票最新 `trade_date`（断点续传）：有则从次日开始，无则从上市日期开始
        b. 若 start_date > today 则跳过（已是最新）
        c. 调用 `StockDailyGateway.fetch_stock_daily(ts_code, start_date, today)`
        d. 调用 `StockDailyRepository.upsert_many(records)` → `uow.commit()`（每只股票独立事务）
     3. 单只股票失败：记录到 `StockDailySyncFailureRepository`（含 start_date/end_date），继续下一只
   - 返回：`SyncHistoryResult(total, success_count, failure_count, synced_days)`

2. **SyncStockDailyIncrement** — 增量同步
   - 参数：`trade_date: date | None`（不传默认使用昨天自然日，调用方负责判断是否为交易日）
   - 依赖：`StockDailyGateway`、`StockDailyRepository`、`UnitOfWork`
   - 流程：
     1. 确定 trade_date（默认 `date.today() - timedelta(days=1)`）
     2. 调用 `StockDailyGateway.fetch_daily_all_by_date(trade_date)`
     3. 调用 `StockDailyRepository.upsert_many(records)` → `uow.commit()`
     4. 失败即回滚抛异常
   - 返回：`SyncIncrementResult(trade_date, synced_count)`

3. **RetryStockDailySyncFailures** — 重试失败记录
   - 参数：`max_retries: int = 3`
   - 依赖：`StockDailyGateway`、`StockDailyRepository`、`StockDailySyncFailureRepository`、`UnitOfWork`
   - 流程：
     1. 查询 `retry_count < max_retries` 且 `resolved = False` 的失败记录
     2. 逐个重试：调用网关（使用记录中的 ts_code + start_date/end_date）→ upsert → commit（每条独立事务）
     3. 成功标记 `resolved = True`；失败递增 `retry_count`
   - 返回：`RetryResult(total, resolved_count, still_failed_count)`

## 6. 接口层设计

### HTTP 端点

- `POST /data-engineering/stock-daily/sync/history` — 触发历史数据同步
  - 请求体（可选）：`{ "ts_codes": ["000001.SZ", ...] }`
  - 响应：`ApiResponse[SyncHistoryResult]`
- `POST /data-engineering/stock-daily/sync/increment` — 触发增量同步
  - 请求体（可选）：`{ "trade_date": "2026-02-19" }`
  - 响应：`ApiResponse[SyncIncrementResult]`
- `POST /data-engineering/stock-daily/sync/retry-failures` — 重试失败记录
  - 请求体（可选）：`{ "max_retries": 3 }`
  - 响应：`ApiResponse[RetryResult]`

### 定时任务

暂不实现，待后续 foundation 模块 scheduler 完善后再添加。

## 7. 错误处理与幂等性

- **幂等性**：以 `(source, third_code, trade_date)` 为唯一键做 upsert（ON CONFLICT DO UPDATE）
- **断点续传**：历史同步前查本地最新 `trade_date`，仅同步增量部分，避免重复拉取
- **历史同步**：每只股票独立事务 + 失败记录表（含日期范围，支持精确重试）
- **增量同步**：整体事务，失败即回滚抛异常
- **限流**：Gateway 内 Token Bucket，每分钟 ≤ 200 次 API 调用
- **最大重试**：失败记录 `retry_count` 达到 `max_retries` 后不再自动重试，需人工介入
- **并发保护**：当前由调用方保证同一时刻不并发触发同类型同步；后续可加分布式锁
