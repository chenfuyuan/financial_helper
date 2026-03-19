## Why

<!-- REASON: 原文痛点描述偏定性（"缺乏统一机制""大量人工介入"），缺乏量化数据，决策者无法评估优先级。补充可量化的成本和频率指标，使动机更具说服力。 -->

当前 data_engineering 模块已实现基于 Tushare 的单日增量同步（`SyncStockDailyIncrement` + `de.sync_stock_daily_increment` 定时任务），但存在以下可量化的痛点：

1. **人工补数成本高**：应用停机后（部署升级、服务器故障等），每缺失 1 天数据需运维手动执行一条补数命令（约 5-10 分钟/次）。停机 3 天即需 15-30 分钟人工介入；停机超 1 周则需编写临时脚本逐日补数，操作失误风险显著上升。
2. **首次全量同步无自动化路径**：从零开始同步历史数据（约 15 年 × ~250 交易日 ≈ 3,750 个交易日）需人工分段执行，预计耗时 4-6 小时且容易遗漏日期区间，导致数据不完整。
3. **数据缺口不可自动发现**：单日增量任务不检查数据库已有同步进度，`trade_date` 参数完全依赖外部传入；静默跳过的交易日无法被系统自动识别和修复，可能导致下游分析模块（市场洞察、知识中心等）使用不完整数据产生错误结论。

为提升数据同步的可靠性与自动化程度，需要一个由应用层统一建模的"股票日线区间增量同步用例"，并通过 foundation 调度器稳定地定时触发。

## In Scope

<!-- REASON: 原文 What Changes 混杂了范围界定与实现方案。拆出显式的 In Scope / Out of Scope，明确项目边界，杜绝范围蔓延。 -->

- 新增 `SyncStockDailyIncrementRange` Command + Handler（区间增量同步用例）
- 统一首次全量与增量策略（首次起点 `2010-01-01` / 增量起点 `latest_trade_date + 1 day`）
- 扩展 `StockDailyRepository` 接口，新增按数据源维度查询全局最新 `trade_date` 方法
- 在 `interfaces/schedulers` 下注册 `de.sync_stock_daily_increment_range` 定时任务
- 按日小事务与幂等 upsert 策略
- 输入参数校验（`end_date` 不晚于 `today`）
- 保留现有 `SyncStockDailyIncrement` 单日增量兼容

## Out of Scope

- 跨模块统一失败记录重试系统（独立失败表 + 自动重试调度）
- 引入新数据源（如 AkShare 日线），仍以 Tushare 为唯一日线数据源
- Foundation 调度器架构重构（持久化 job store、分布式调度）
- HTTP API 行为变更（不影响现有路由）
- 交易日历服务（本次使用自然日遍历，非交易日视为空操作）
- 数据回溯清洗（仅同步新数据，不重新修正历史记录）
- Tushare API 限流 / 熔断机制（本次仅预留扩展点，不实现）

## What Changes

- 新增 **区间增量同步用例**：在 data_engineering 应用层引入 `SyncStockDailyIncrementRange` Command + Handler，根据数据库当前最新 Tushare 日线 `trade_date` 自动计算需补齐的日期区间 `[start_date, end_date]`，并按日补齐到目标结束日期（默认 `today - 1 day`）。
- 规范 **首次全量与后续增量策略**：当数据库无 Tushare 日线数据时，从 `2010-01-01` 起全量补数；有数据时从 `latest_trade_date + 1 day` 起增量补齐，避免重复拉取与写入。
- 扩展 **仓储接口**：在 `StockDailyRepository` 中新增 `get_latest_trade_date_by_source(source: DataSource) -> date | None`，按数据源维度查询全局最新交易日期（不再依赖 `third_code` 维度）。
- 接入 **foundation 调度器**：在 `interfaces/schedulers` 下新增 `de.sync_stock_daily_increment_range` 任务，复用 `ScheduledTaskConfig + CronTrigger + ModuleRegistry` 机制，应用启动时统一注册。
- 明确 **按日小事务与幂等策略**：Handler 内按交易日划分事务，单日失败不影响其他日期；依赖 `(source, third_code, trade_date)` 唯一键 + upsert 保证重复执行不产生重复数据。
- 保持 **单日增量用例兼容**：保留 `SyncStockDailyIncrement` 能力，定位为运维场景下的单日手工补数或临时修正工具。

## Capabilities

### New Capabilities

- `data-engineering-stock-daily-incremental-range-sync`: 为股票日线数据提供应用层建模的"区间增量同步"能力，支持从固定历史起点（`2010-01-01`）到指定结束日期的自动补数，多次执行自动续传、容忍中断和重复执行。
- `data-engineering-scheduler-integration-for-incremental-sync`: 基于 foundation 调度器的增量同步调度集成能力，通过 `interfaces/schedulers` 定义任务配置和 async callable，使区间增量用例在无 HTTP 上下文下安全管理 Session/UoW 生命周期并被定时触发。

### Modified Capabilities

- `data-engineering-stock-daily-sync`: "股票日线同步"能力扩展为同时支持单日增量与区间增量，需求层面增加首次全量补数、自动识别缺口日期区间、幂等重入等行为约束。

## Impact

- **受影响代码模块**
  - `src/app/modules/data_engineering/application/commands/`：新增区间增量 Command/Handler。
  - `src/app/modules/data_engineering/domain/repositories/`：`StockDailyRepository` 新增 `get_latest_trade_date_by_source` 抽象方法。
  - `src/app/modules/data_engineering/infrastructure/repositories/`：`SqlAlchemyStockDailyRepository` 实现新仓储方法（`MAX(trade_date) WHERE source = ?` 聚合查询）。
  - `src/app/modules/data_engineering/interfaces/schedulers/`：`tasks.py` 新增任务配置与 async callable。
- **调度与运行时影响**
  - Foundation 调度器新增一个 data_engineering 任务（`de.sync_stock_daily_increment_range`），启动时注册并定时触发。
  - 首次全量补数可能产生约 3,750 次 Tushare API 调用和相应的数据库 upsert 写入（每次约 5,000 条记录），需关注 Tushare 限流策略与数据库 I/O 负载。
- **文档与规范**
  - 需新增 `data-engineering-stock-daily-incremental-range-sync` 的 spec 文件（已包含在本变更中）。
  - 建议更新 `docs/design/financial-helper/modules/data-engineering.md` 模块文档。

## Risks

<!-- REASON: 原文将风险完全放在 design.md 中，proposal 层面无法让审批者在立项阶段评估技术风险。将核心风险提前到 proposal，并新增原文未覆盖的 2 条风险（Tushare Token 失效、stock_basic 映射不完整）。 -->

| # | 风险描述 | 严重程度 | 概率 | 缓解 / 回滚方案 |
|---|---------|---------|------|-----------------|
| R1 | 首次全量补数跨越约 3,750 个交易日，Tushare API 限流（积分消耗）或数据库写入压力过大，单次任务耗时可能超过 2 小时 | 高 | 中 | Handler 预留 `max_days_per_run` 扩展点；支持通过 `end_date` 分段补数；`misfire_grace_time=7200` 容忍延迟执行 |
| R2 | 某些日期同步失败导致"中间缺天"，下游分析模块使用不完整数据 | 中 | 中 | Result 显式返回 `failed_dates`；日志清晰记录失败原因；可通过单日增量或指定 `end_date` 的区间增量补救 |
| R3 | <!-- REASON: 新增风险——原文未考虑 Token 失效场景。长区间补数可能持续数小时，期间 Token 可能过期或被平台吊销。 --> **Tushare Token 过期或被吊销**：长区间补数过程中 Token 失效，后续所有日期均返回认证失败 | 高 | 低 | Gateway 层捕获认证失败错误后立即终止循环（fail-fast），避免无意义重试消耗剩余积分；运维监控 Token 有效期并提前告警 |
| R4 | <!-- REASON: 新增风险——原文未考虑 stock_basic 数据依赖。区间增量依赖 stock_basic 做 third_code → symbol 映射，若基础数据未同步则 symbol 全部缺失。 --> **stock_basic 映射数据不完整或为空**：`StockBasicRepository` 中的股票基础信息未同步或不完整，导致部分/全部 `third_code` 无法映射到 `symbol` | 中 | 低 | Handler 启动时校验 stock_basic 数据非空，空则记录 warning 并提前退出或降级执行；未匹配的 `third_code` 在日志中记录但不阻塞同步 |
| R5 | 区间增量 Handler 复杂度高于单日 Handler，两套用例并存增加维护负担 | 低 | 高 | 拆分清晰步骤 + 充分单元测试确保可维护性；中长期根据使用情况考虑合并或废弃单日用例 |
