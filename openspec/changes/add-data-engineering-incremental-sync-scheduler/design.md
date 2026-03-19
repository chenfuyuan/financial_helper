## Context

data_engineering 模块已具备基于 Tushare 的单日增量同步能力（`SyncStockDailyIncrement` Command/Handler + `de.sync_stock_daily_increment` 定时任务），并通过 foundation 调度器（`Scheduler` Protocol + `AsyncIOSchedulerImpl` + `ModuleRegistry`）接入。但当前调度任务只按"某一天"执行，应用层缺乏统一建模的区间增量用例，导致首次全量补数、停机后多日补齐、幂等续传等场景需要人工驱动。本设计在不改动 foundation 调度抽象的前提下，为 data_engineering 新增一个"日线区间增量同步"应用用例，并通过既有调度接入模式定时触发。

## Goals / Non-Goals

**Goals:**

- 在 data_engineering 应用层新增 `SyncStockDailyIncrementRange` Command + Handler，用于根据数据库当前最新 Tushare 日线数据自动计算需要补齐的日期区间，并按日补齐到指定结束日期（默认 `today - 1 day`）。
- 统一首次全量与后续增量策略：首次从 `2010-01-01` 起补数，有数据后从 `latest_trade_date + 1 day` 起增量补齐，确保多次执行幂等、可续传。
- 在 `interfaces/schedulers` 下为区间增量用例新增调度任务（`de.sync_stock_daily_increment_range`），复用 `ScheduledTaskConfig + CronTrigger + ModuleRegistry` 机制，在应用启动时统一完成注册与启动。
- 对 `end_date` 参数进行校验，拒绝晚于 `today` 的未来日期。
<!-- REASON: 新增——与 spec_optimized.md 中新增的输入校验需求对齐。 -->
- 保持与现有单日增量用例兼容，支持运维场景下的手动单日补数。

**Non-Goals:**

- 不设计或实现跨模块的统一"失败记录重试系统"（如独立失败表、重试策略），只在 Result 中返回失败日期列表并通过日志暴露。
- 不在本变更中引入新的数据源（如 AkShare 日线），仍以 Tushare 为唯一日线数据源。
- 不重构 foundation 调度器架构（如引入持久化 job store、分布式调度），仅在 data_engineering 侧增加任务和用例。
- 不修改现有 HTTP API 行为（如 stock_daily 的路由），本次改动只影响后台同步和调度逻辑。
- 不实现 Tushare API 层面的熔断器或限流器（仅预留扩展点）。
<!-- REASON: 与 proposal_optimized.md 的 Out of Scope 对齐。 -->

## Decisions

### 1. 在 Application 层显式建模区间增量用例

- **决策**：新增 `SyncStockDailyIncrementRange` Command + Handler，Handler 内部负责读取最新 `trade_date`、计算补数区间、按日循环同步、聚合结果。

<!-- REASON: 为每个决策补充显式的 Trade-off 分析表，使决策理由更透明、备选方案更清晰。 -->

| 维度 | 选择方案（Application 层建模） | 备选方案（Interfaces 层脚本式循环） |
|------|-------------------------------|-----------------------------------|
| 可测试性 | Handler 可独立单元测试，Mock 依赖即可 | 脚本与 session/scheduler 耦合，需集成测试 |
| 复用性 | 其他入口（HTTP API、CLI）均可调用同一 Handler | 逻辑绑定在 scheduler callable 中，难以复用 |
| 复杂度 | Handler 内部逻辑较多，需拆分清晰步骤 | 脚本简单直接，但业务规则分散 |
| **Trade-off** | **增加 Application 层代码量，但获得显著更好的可测试性和可维护性** | |

### 2. 首次同步起点与增量策略

- **决策**：
  - 若 `latest_trade_date is None`：`start_date = date(2010, 1, 1)`
  - 否则：`start_date = latest_trade_date + 1 day`
  - 默认 `end_date = today - 1 day`，Command 允许自定义 `end_date`（MUST 不晚于 `today`，否则拒绝）

| 维度 | 选择方案（固定起点 `2010-01-01`） | 备选方案（配置化起点） |
|------|----------------------------------|---------------------|
| 简单性 | 硬编码，零配置成本 | 需新增配置项、校验逻辑 |
| 灵活性 | 覆盖近 15 年数据，满足当前需求 | 可覆盖任意历史区间 |
| 维护性 | 修改需改代码 | 改配置即可 |
| **Trade-off** | **简单清晰，初版足够；若未来需要更早数据可通过 `end_date` 手动指定或升级为配置化** | |

<!-- REASON: 补充 end_date 校验逻辑，与 spec 中新增的输入校验需求一致。 -->

- **end_date 校验**：当传入 `end_date > date.today()` 时，Handler MUST 抛出 `ValueError`（或对应领域异常），不执行任何同步。理由：Tushare 在未来日期无数据可返回，允许未来日期只会产生全部失败的无意义执行。

### 3. 按日小事务与幂等实现方式

- **决策**：Handler 内对 `[start_date, end_date]` 的每一天使用独立事务（`async with uow`），单日成功后提交，单日失败不回滚其他日期。依赖 `StockDailyRepository.upsert_many` 及 `(source, third_code, trade_date)` 唯一键实现幂等。

| 维度 | 选择方案（按日小事务 + upsert 幂等） | 备选方案 A（整体大事务） | 备选方案 B（同步进度表） |
|------|-------------------------------------|------------------------|------------------------|
| 故障恢复 | 单日失败不影响已提交数据，渐进式修复 | 任一日失败则全部回滚 | 精确记录进度，但增加状态管理 |
| 性能 | 每日一次 commit，事务开销可控 | 长事务锁定时间长 | 额外进度表读写开销 |
| 幂等性 | upsert 天然幂等 | 需额外判断"是否已存在" | 进度表本身也需幂等 |
| 复杂度 | 中等 | 低 | 高 |
| **Trade-off** | **事务粒度适中，兼顾故障恢复与简单性；大量重复执行时会产生无效 upsert 但不破坏数据正确性** | | |

### 4. 仓储接口扩展方式

- **决策**：在 `StockDailyRepository` 接口中新增 `get_latest_trade_date_by_source(source: DataSource) -> date | None`，`SqlAlchemyStockDailyRepository` 通过 `SELECT MAX(trade_date) FROM stock_daily WHERE source = :source` 实现。

| 维度 | 选择方案（按 source 全局聚合） | 备选方案（遍历所有 third_code 取最小的 latest） |
|------|-------------------------------|-----------------------------------------------|
| 性能 | 单次聚合查询，O(1) | 需查询所有 third_code 再取 MIN，O(N) |
| 语义 | "全市场同步到哪一天" | "最落后的个股到哪一天"（更保守但更慢） |
| **Trade-off** | **全局 MAX 简单高效，但可能遗漏个别股票的缺失天——当前按日全市场拉取的模型下此问题不存在** | |

### 5. 调度接入与任务命名

- **决策**：在 `data_engineering/interfaces/schedulers/tasks.py` 中新增任务：

```python
ScheduledTaskConfig(
    id="de.sync_stock_daily_increment_range",
    trigger=CronTrigger(hour=16, minute=30),
    name="同步股票日线增量（区间）",
    module="data_engineering",
    max_instances=1,
    coalesce=True,
    misfire_grace_time=7200,
)
```

| 维度 | 选择方案 | 说明 |
|------|---------|------|
| 触发时间 | `16:30`（收盘后 30 分钟） | 与现有单日任务一致，减少运维认知负担 |
| `max_instances=1` | 防止并发执行 | 区间增量不支持并发，依赖数据库状态 |
| `coalesce=True` | 合并错过的执行 | 避免应用重启后重复触发多次 |
| `misfire_grace_time=7200` | 2 小时补执行窗口 | 容忍部署/重启延迟 |
| **Trade-off** | **与单日任务时间重叠，可能产生竞争（均在 16:30 触发）；但 `max_instances=1` 和独立事务保证数据安全** | |

<!-- REASON: 指出两个任务时间重叠的隐患——原文未提及。建议在实施时考虑错开时间或禁用旧任务。 -->

> **实施建议**：建议将区间增量任务的触发时间调整为 `16:45` 或 `17:00`，避免与现有单日任务同时触发；或在启用区间增量后禁用旧的单日增量定时任务（保留 Handler 供手动调用）。

### 6. 保留单日增量用例

- **决策**：保留 `SyncStockDailyIncrement` Command/Handler 和 `de.sync_stock_daily_increment` 任务，区间增量为推荐默认方式，单日增量定位为运维手动补数工具。
- **Trade-off**：维护两套用例增加代码认知负担，但提供了灵活性和回滚后路；中长期可根据实际使用情况决定是否废弃单日用例。

### 7. 网关异常处理策略

<!-- REASON: 新增决策——与 spec_optimized.md 中新增的"处理网关异常与超时"需求对齐。原文 design 缺少对不同异常类型的分级处理策略。 -->

- **决策**：区分两类网关异常并采取不同策略：

| 异常类型 | 处理策略 | 理由 |
|---------|---------|------|
| 瞬时错误（超时、网络中断、5xx） | 标记该日失败，继续后续日期 | 瞬时问题通常不影响后续请求 |
| 认证错误（Token 过期/无效） | 标记该日失败，**终止**后续同步循环 | 认证失败意味着后续请求必然也会失败，继续执行只会浪费时间和积分 |
| 其他未知异常 | 标记该日失败，继续后续日期 | 保守策略，最大化已同步进度 |

### 8. stock_basic 映射缺失的降级策略

<!-- REASON: 新增决策——与 spec_optimized.md 中新增的"处理 stock_basic 映射缺失"需求对齐。 -->

- **决策**：
  - 若 `StockBasicRepository.find_all(DataSource.TUSHARE)` 返回空列表：记录 warning 日志，继续执行（所有记录的 `symbol` 为空）。
  - 若部分 `third_code` 未匹配到 `symbol`：该记录的 `symbol` 保持空值，正常写入，在日志中记录未匹配数量。
- **Trade-off**：牺牲了 `symbol` 字段的完整性，但保证了日线数据的及时入库；下游如需 `symbol` 可在 stock_basic 数据补全后通过数据修复任务回填。

## API Schema

<!-- REASON: 新增章节——原文 design 缺少统一的接口定义，与 spec 中 Result 字段表格对齐。 -->

### Command

```python
@dataclass(frozen=True)
class SyncStockDailyIncrementRange(Command):
    """区间增量同步指令。"""
    end_date: date | None = None
```

### Result

```python
@dataclass(frozen=True)
class SyncStockDailyIncrementRangeResult:
    """区间增量同步结果。"""
    start_date: date
    end_date: date
    synced_days: int
    synced_records: int
    failed_dates: list[date]
```

### 仓储接口扩展

```python
# StockDailyRepository 新增方法
@abstractmethod
async def get_latest_trade_date_by_source(self, source: DataSource) -> date | None:
    """查询指定数据源下全局最新的 trade_date，用于区间增量计算。无记录返回 None。"""
```

### 错误码与异常

<!-- REASON: 新增——原文未定义错误码，不利于上游调用方统一处理。 -->

| 错误场景 | 异常类型 | 说明 |
|---------|---------|------|
| `end_date > today` | `ValueError` | 拒绝未来日期 |
| 网关认证失败 | `GatewayAuthenticationError`（待定义） | Token 过期/无效，触发 fail-fast |
| 网关超时/网络错误 | `GatewayTimeoutError`（现有或待定义） | 标记单日失败，不中断循环 |

## Architecture

<!-- REASON: 新增章节——对照 spec 检查单点故障并给出缓解方案。 -->

### 单点故障分析

| 组件 | 是否单点 | 缓解措施 |
|------|---------|---------|
| Tushare API | **是**（唯一数据源） | 本次不引入备选数据源（Out of Scope）；通过失败日期列表 + 重试机制确保可恢复；未来可扩展 AkShare 作为 fallback |
| APScheduler（内存模式） | **是**（无持久化 job store） | 依赖 `coalesce=True` + `misfire_grace_time=7200` 容忍重启后的补执行；区间增量本身具备断点续传能力，重启后自动从最新进度继续 |
| PostgreSQL | 否（标准部署含备份） | upsert 幂等保证重复执行安全 |

### 数据流

```
Scheduler (CronTrigger 16:30)
    │
    ▼
interfaces/schedulers/tasks.py
    │  创建 Session, 构造 Handler
    ▼
SyncStockDailyIncrementRangeHandler.handle(command)
    │
    ├─ 1. StockDailyRepository.get_latest_trade_date_by_source(TUSHARE)
    │     → latest_trade_date | None
    │
    ├─ 2. 计算 [start_date, end_date]
    │     → 若 start_date > end_date: 返回零值 Result
    │
    ├─ 3. StockBasicRepository.find_all(TUSHARE)
    │     → symbol_map: dict[third_code, symbol]
    │
    └─ 4. for d in [start_date, end_date]:
          │
          ├─ async with uow:
          │    ├─ StockDailyGateway.fetch_daily_all_by_date(d)
          │    ├─ 填充 symbol (from symbol_map)
          │    ├─ StockDailyRepository.upsert_many(records)
          │    └─ uow.commit()
          │
          └─ on exception:
               ├─ 认证错误 → fail-fast, break
               └─ 其他错误 → 记录 failed_dates, continue
```

## Risks / Trade-offs

- **[风险] 首次从 2010-01-01 起补数可能跨越约 3,750 个交易日，Tushare 限流与数据库写入压力较大**
  → **缓解**：在 Handler 中预留 `max_days_per_run` 扩展点（初版不限制），可通过配置快速收紧；支持通过 `end_date` 分段补数。

- **[风险] 某些日期同步失败但整体任务继续执行，可能导致"中间缺天"**
  → **缓解**：Result 显式返回 `failed_dates`，日志清晰记录；后续调度执行时，由于 `latest_trade_date` 基于全局 MAX，失败日期之前的天数不会被重新同步。**需注意**：若第 N 天失败但第 N+1 天成功，`latest_trade_date` 会推进到 N+1，第 N 天的缺口需要手动通过单日增量补救。
  <!-- REASON: 明确指出了原文隐含但未显式说明的"失败日期不会被自动重试"的问题——这是一个重要的运维注意事项。 -->

- **[权衡] 默认 `end_date = today - 1 day` 而非 `today`，当日数据延迟一天可用**
  → **理由**：Tushare 在收盘前或刚收盘后数据可能不稳定，延迟一天降低脏数据风险；需当日数据可通过 `end_date=today` 或单日增量补齐。

- **[风险] Tushare Token 在长区间补数过程中过期或被吊销**
  → **缓解**：Handler 对认证错误实施 fail-fast 策略（Decision 7），避免无意义重试消耗积分；运维层面监控 Token 有效期。
  <!-- REASON: 新增——与 proposal_optimized.md 风险 R3 和 spec_optimized.md 认证失败场景对齐。 -->

- **[风险] stock_basic 映射数据不完整导致 `symbol` 字段缺失**
  → **缓解**：降级策略（Decision 8）允许 `symbol` 为空的记录写入，保证日线数据不因映射问题而丢失；下游消费方需容忍 `symbol` 可能为空。
  <!-- REASON: 新增——与 proposal_optimized.md 风险 R4 和 spec_optimized.md 映射缺失需求对齐。 -->

- **[风险] 区间增量的逻辑集中在一个 Handler 中，复杂度高于单日 Handler**
  → **缓解**：拆分清晰小步骤（读取最新日期 → 计算区间 → 按日同步 → 结果汇总），每步可独立测试；保留单日 Handler 作为备用。

- **[权衡] 依赖 `(source, third_code, trade_date)` 唯一键 + upsert 实现幂等，而非引入"同步进度表"**
  → **理由**：当前需求下唯一键策略足够，避免引入新的状态存储；逻辑错误导致的重复执行会产生无效 upsert 但不破坏数据正确性，可通过监控写入量追踪。

- **[风险] 两个定时任务（单日 16:30 + 区间 16:30）同时触发可能产生资源竞争**
  → **缓解**：建议将区间任务触发时间调整为 `16:45` 或 `17:00`，或在启用区间增量后禁用旧的单日定时任务。
  <!-- REASON: 新增——原文未考虑两个任务时间重叠的问题。 -->

## Migration Plan

- **阶段 1：实现与测试**
  - 在 data_engineering 应用层实现 `SyncStockDailyIncrementRange` Command/Result 以及 Handler，包含 `end_date` 校验、区间计算、按日同步、异常分级处理（Decision 7）、stock_basic 映射降级（Decision 8）。
  - 在 `StockDailyRepository` / `SqlAlchemyStockDailyRepository` 中新增 `get_latest_trade_date_by_source` 方法。
  - 编写单元测试（Mock Gateway/Repository/UoW）覆盖 spec 中所有 Scenario。
  - 在 `interfaces/schedulers/tasks.py` 中新增 `de.sync_stock_daily_increment_range` 任务及其 async callable。

- **阶段 2：灰度启用**
  - 在测试/预发布环境中启用区间增量任务，观察首次大区间补数的表现（耗时、Tushare 调用量、数据库负载）。
  - 验证多次执行的幂等性以及中断后自动续传能力。
  - 验证认证失败 fail-fast 和 stock_basic 空映射降级行为。

- **阶段 3：生产启用与监控**
  - 在生产环境启用 `de.sync_stock_daily_increment_range` 任务。初期可降低频率（手动触发），确认正常后调整为每日定时。
  - 为关键日志添加监控规则（连续多日 `failed_dates` 非空、`synced_days` 异常大、认证失败告警等）。
  - 考虑禁用旧的 `de.sync_stock_daily_increment` 定时任务（保留 Handler 供手动调用）。

- **回滚策略**
  - 若区间增量任务出现严重问题，可在不改动代码的情况下禁用该调度任务（移除 `ScheduledTaskConfig` 或通过配置开关），回退到现有单日增量任务。
  - 由于 upsert 幂等，区间增量写入的数据不会破坏已有数据完整性。

## Open Questions

- 是否需要在首轮大区间补数时显式限制"单次最大覆盖天数"（如 30 天），将多年补数拆分为多次调度？还是先观察实际负载再决定。
- 对于失败日期的处理是否需要在短期内引入"失败记录表 + 自动重试任务"，还是暂时依赖日志与手动补救。
- 认证失败的 fail-fast 行为是否需要通过领域事件通知外部监控系统（如发送告警邮件/消息），还是仅依赖日志。
<!-- REASON: 新增 open question——认证失败的外部通知策略值得讨论。 -->
- 两个定时任务（单日 + 区间）长期共存是否合理，还是在区间增量稳定后直接禁用单日定时任务。
