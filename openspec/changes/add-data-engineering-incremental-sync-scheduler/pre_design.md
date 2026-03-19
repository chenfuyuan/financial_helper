# 数据工程日线增量同步调度 Pre-Design

**日期:** 2026-03-19  
**状态:** 草案（pre_design）  
**类型:** 数据工程模块增量同步 + 调度集成

---

## 1. 背景与目标

当前项目已落地 foundation 调度器（APScheduler + `ModuleRegistry`），并为 data_engineering 模块实现了「按单个交易日全市场增量同步」的指令：

- Command: `SyncStockDailyIncrement`
- Handler: `SyncStockDailyIncrementHandler`
- 定时任务：`de.sync_stock_daily_increment`（每天 16:30 拉取前一交易日全市场日线）

现存问题与缺口：

1. **只支持“单日增量”，不支持自动补齐历史缺口**  
   - 若应用长时间停机，期间多天未同步，需要手工补数。
   - 无法统一处理「首次全量」与「后续增量」。
2. **同步范围完全由任务配置决定**  
   - 现有任务只传 `trade_date`，不知道数据库当前已经有多少历史数据。

本变更的目标：

> 在不破坏现有 foundation 调度架构的前提下，为 data_engineering 模块设计并落地一个“**按区间补齐股票日线数据**”的应用用例，并通过调度器定时触发，实现：
>
> - 首次从 **2010-01-01** 起全量回补到指定结束日期；
> - 之后每次自动从「数据库最新 trade_date + 1 日」补到「当前（或最近一个）可同步日期」；
> - 多次执行幂等，支持中断后自动续传。

---

## 2. 关键设计决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 用例建模 | 新增 `SyncStockDailyIncrementRange` Command + Handler | 区间增量是独立应用用例，应集中到 application 层建模 |
| 数据源 | 使用 **Tushare** 日线 API（现有 `TuShareStockDailyGateway`） | 与当前实现保持一致，避免同时引入新数据源 |
| 首次同步起点 | 固定为 `2010-01-01` | 简单清晰，覆盖近十多年 A 股历史数据 |
| 增量起点 | `max(trade_date where source=TUSHARE) + 1 day` | 与当前表结构和唯一键约束一致 |
| 结束日期 | 默认 `today - 1 day` | 避免当日收盘前数据不稳定；未来可配置 |
| 事务粒度 | 默认 **按交易日小事务** | 单日失败不影响已完成日期，利于长区间补数与故障恢复 |
| 幂等性 | 依赖 `(source, third_code, trade_date)` 唯一键 + upsert | 允许重复执行同一区间而不会产生重复数据 |
| 调度接入方式 | 通过 data_engineering 的 `interfaces/schedulers/tasks.py` 注册新任务 | 复用既有 foundation 调度集成模式，保持依赖方向正确 |

---

## 3. 用例与数据流设计

### 3.1 新增用例：SyncStockDailyIncrementRange

**用例描述：**

- 场景：股票日线数据同步（数据源 Tushare）
- 参与者：系统调度器（每天定时）、运维人员（可手动触发）
- 目标：根据当前数据库中已有的 Tushare 日线数据，自动计算需要补齐的日期区间，并按日补齐至目标结束日期。

**Command（草案）：**

- 名称：`SyncStockDailyIncrementRange`
- 字段（初版）：
  - `end_date: date | None = None`  
    - 不传：使用 `today - 1 day`  
    - 允许传入自定义结束日期，便于手动补数或回溯

**Result（草案）：**

- `start_date: date` — 实际补数起始日期
- `end_date: date` — 实际补数结束日期
- `synced_days: int` — 成功同步的天数
- `synced_records: int` — 成功 upsert 的总记录数
- `failed_dates: list[date]` — 同步失败的交易日列表（错误已记录日志）

### 3.2 处理流程

1. **确定结束日期**
   - 若 Command 未传 `end_date`：  
     - 使用 `today - 1 day` 作为结束日期（后续可改为交易日历）。
   - 若传入 `end_date`：  
     - 使用传入值，但需校验不晚于 `today`，防止误传未来日期。

2. **读取数据库最新同步点**
   - 从 `StockDailyRepository` 查询：  
     - `latest_trade_date = max(trade_date) where source = DataSource.TUSHARE`
   - 两种情况：
     - 若 `latest_trade_date` 为 `None`：认为**从未同步过**；
     - 否则：认为已经同步到了 `latest_trade_date`。

3. **计算补数起始日期**
   - 若 `latest_trade_date is None`：  
     - `start_date = date(2010, 1, 1)`（固定起点）
   - 否则：  
     - `start_date = latest_trade_date + 1 day`

4. **区间有效性检查**
   - 若 `start_date > end_date`：  
     - 无需执行任何同步，直接返回空结果（synced_days=0, synced_records=0）。

5. **按日循环同步**
   - 对于 `d` in `[start_date, end_date]`（包含端点）：
     1. 调用 `StockDailyGateway.fetch_daily_all_by_date(d)` 拉取全市场日线；
     2. 使用 `StockBasicRepository.find_all(DataSource.TUSHARE)` 构造 `third_code -> symbol` 映射（可考虑缓存）；  
        - 将每条 `StockDaily` 记录的 `symbol` 字段补齐；
     3. 调用 `StockDailyRepository.upsert_many(records)` 写入；  
        - 利用 `(source, third_code, trade_date)` 唯一键 + upsert 实现幂等。
     4. 每日同步成功后，累加计数并记录结构化日志。

6. **异常处理策略（按日小事务）**
   - 每个交易日使用独立事务（`async with uow`），成功即 `commit`。
   - 某日同步失败：
     - 记录 error 日志：包含 `trade_date`, `error`, `stack`；
     - 将该日期加入 `failed_dates`；
     - 不中断总体循环，继续后续日期。

7. **结果汇总**
   - 生成 `SyncStockDailyIncrementRangeResult`，包含：
     - 起止日期、成功天数、总记录数、失败日期列表。
   - 在 Handler 结束时打 info 日志，用于运维观测。

---

## 4. 与现有单日增量用例的关系

现有单日增量用例：

- Command: `SyncStockDailyIncrement(trade_date: date | None)`
- Handler: `SyncStockDailyIncrementHandler`
  - 默认 `trade_date = today - 1 day`
  - 行为：对单一 `trade_date` 拉全市场 Tushare 日线并 upsert。

本次新用例的关系与取舍：

1. **不直接复用现有 Handler 进行 for 循环**  
   - 原因：  
     - 区间计算、异常聚合、结果统计等逻辑属于新的应用用例；  
     - 若仅在 interfaces 层“脚本式 for 循环调用旧 Handler”，容易让业务规则分散难以测试。
2. **短期内两个用例可以并存**  
   - `SyncStockDailyIncrement`：仍可用于「手动指定某日补数」的场景（如运营临时修复）；  
   - `SyncStockDailyIncrementRange`：作为调度任务和主用例，负责自动补齐历史缺口。
3. **后续可能的简化路径**  
   - 若实践证明“区间用例足够覆盖所有场景”，可考虑用 Range Handler 内部调用单日 Handler，逐步弱化或废弃单日用例。

---

## 5. 调度与集成设计

### 5.1 新的调度任务

在 `src/app/modules/data_engineering/interfaces/schedulers/tasks.py` 中：

- 新增任务配置：
  - `id`: `de.sync_stock_daily_increment_range`
  - `name`: `同步股票日线增量（区间）`
  - `module`: `data_engineering`
  - `trigger`: `CronTrigger(hour=16, minute=30)`（可与原任务共存或替换）
  - `max_instances`: `1`
  - `coalesce`: `True`
  - `misfire_grace_time`: `7200`

- 对应 async callable：
  - 通过 `session_factory` 创建 `AsyncSession`；
  - 构造：
    - `SqlAlchemyStockDailyRepository`
    - `SqlAlchemyStockBasicRepository`
    - `TuShareStockDailyGateway`
    - `SqlAlchemyUnitOfWork`
    - 新的 `SyncStockDailyIncrementRangeHandler`
  - 构造默认 Command：`SyncStockDailyIncrementRange()`（不传 `end_date`）；
  - 执行 `handler.handle(command)`，记录结果日志。

### 5.2 与 foundation 调度器的集成

沿用既有模式：

- `data_engineering/interfaces/schedulers/__init__.py`：
  - `create_scheduled_tasks(session_factory)` 返回：
    - `configs: list[ScheduledTaskConfig]`（包括新任务）
    - `task_callables: dict[id, async_callable]`
- `app.modules.register_scheduled_tasks()` 已经将 data_engineering 的 factory 注册到 `ModuleRegistry`。
- `interfaces/main.py` 中 `_initialize_scheduler()` 会：
  - 创建 `ModuleRegistry`；
  - 调 `app.modules.register_scheduled_tasks(registry, db.session_factory)`；
  - 调 `registry.register_all_to_scheduler(scheduler)`；
  - 由 foundation 的 `AsyncIOSchedulerImpl` 完成任务注册与启动。

---

## 6. 风险与边界情况

1. **长区间首次全量（2010-01-01 起）耗时与压力**  
   - 风险：首次执行可能跨越多年交易日，Tushare 限流与数据库写入压力较大；  
   - 缓解：
     - 在 Handler 内增加“单次任务最大天数”限制（如最多补 30 天），多次调度逐步补齐；
     - 或在配置中通过 `end_date` 分段执行。

2. **非交易日处理**  
   - 若 `fetch_daily_all_by_date(d)` 在非交易日返回空列表：  
     - 视为正常情况，记录 debug/info 日志后继续；
     - 不应该视为失败。

3. **失败日期后续处理策略**  
   - 当前设计中失败日期会被记录在 `failed_dates`；  
   - 下次执行时，由于 `latest_trade_date` 已被成功日期推进，失败日期仍会被视为“未补齐”，可通过手动指定 `end_date` 或单日用例进行补救；  
   - 未来可考虑引入“失败记录表”与重试机制（不在本次变更范围内）。

---

## 7. 待办事项（ToDo 清单）

- [ ] 定义 `SyncStockDailyIncrementRange` Command 与 Result 数据结构
- [ ] 实现 `SyncStockDailyIncrementRangeHandler`，包含：
  - [ ] 读取最新 trade_date（按 Tushare source）
  - [ ] 计算起止日期区间与边界检查
  - [ ] 按日循环调用 gateway + repository + uow
  - [ ] 完整的结构化日志与错误处理
- [ ] 为 `StockDailyRepository` / `SqlAlchemyStockDailyRepository` 扩展“按 source 查询全局最新 trade_date”的接口/实现（如尚未满足需求）
- [ ] 在 `data_engineering/interfaces/schedulers/tasks.py` 中新增 `de.sync_stock_daily_increment_range` 任务配置与 async callable
- [ ] 决定旧任务 `de.sync_stock_daily_increment` 的去留策略（保留用于手动单日补数，或直接替换）
- [ ] 编写对应的单元测试与集成测试用例
- [ ] 在需要时更新文档（如 `docs/design/financial-helper/modules/data-engineering.md` 或相关使用指南），说明区间增量用例的行为与使用方式

