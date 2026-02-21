## MODIFIED Requirements

### Requirement: 全市场历史财务指标全量同步

系统 MUST 支持一次性触发针对全市场所有已知股票的历史财务指标（`fina_indicator`）的全量拉取与入库，数据存储到 `stock_financial` 表中。

#### Scenario: 首次全量同步

- **GIVEN** 系统中已有通过 `stock_basic` 同步获取的全市场股票列表
- **WHEN** 全市场全量同步流程被触发时
- **THEN** 系统从 `StockBasicRepository` 获取所有已知股票的 `third_code` 列表
- **AND** 系统在进程生命周期内维护一个 `Set[str]` 记录已完成同步的 `third_code`，防止同一运行时重复处理
- **AND** 系统按顺序迭代拉取每只股票的全部历史财务指标，复用 `TokenBucket` 限流器遵守 200次/分钟频控
- **AND** 对于单只股票拉取，如果单次 API 返回恰好 100 条记录，系统 MUST 自动进行分页拉取，直到返回不足 100 条
- **AND** 系统将拉取到的数据以 `(source, third_code, end_date)` 为冲突键 Upsert 入库到 `stock_financial` 表
- **AND** 每只股票独立事务提交，单只股票失败不影响其他股票的同步

#### Scenario: 全量同步过程中单只股票拉取失败

- **GIVEN** 全量同步正在进行中
- **WHEN** 某只股票的 API 调用抛出异常时
- **THEN** 系统 MUST 记录错误日志（包含 `third_code` 和异常详情）
- **AND** 系统跳过该股票继续处理下一只
- **AND** 最终返回包含 `total`、`success_count`、`failure_count` 的汇总结果

#### Scenario: 全量同步幂等性

- **GIVEN** 全量同步曾中途中断（进程崩溃）
- **WHEN** 再次触发全量同步时
- **THEN** 系统从零开始遍历所有股票
- **AND** 已存在的数据通过 Upsert 幂等覆盖到 `stock_financial` 表，不产生重复或脏数据

---

### Requirement: 按单只股票历史同步

系统 MUST 支持拉取并存储限定于特定股票（`third_code`）的全部历史财务指标数据到 `stock_financial` 表。

#### Scenario: 单只股票修复或显式同步

- **GIVEN** 调用方提供了一个有效的 `third_code`
- **WHEN** 针对该 `third_code` 触发同步时
- **THEN** 系统通过 `fina_indicator` 接口（标准接口，2000积分）获取该股票所有历史财务指标
- **AND** 如果单次返回 100 条，系统自动分页拉取剩余数据
- **AND** 系统将数据以 `(source, third_code, end_date)` 为冲突键 Upsert 入库到 `stock_financial` 表
- **AND** 返回包含 `third_code` 和 `synced_count` 的结果

#### Scenario: 该股票无财务指标数据

- **WHEN** API 返回空数据时
- **THEN** 系统记录信息日志并返回 `synced_count=0`
- **AND** 不抛出异常

---

### Requirement: 增量同步（逐股票断点续传）

系统 MUST 支持基于本地已有数据的增量同步，用于日常定时任务高效拉取最新财务指标到 `stock_financial` 表。

> [!NOTE]
> 由于当前仅有 2000 积分，无法使用 `fina_indicator_vip` 按 `ann_date` 查全市场。
> 增量同步采用逐股票遍历 + 本地 `end_date` 断点续传的策略。

#### Scenario: 已完成全量同步后的日常增量

- **GIVEN** 系统已完成全量同步，本地 `stock_financial` 表中大部分股票已有历史数据
- **WHEN** 增量同步被触发时
- **THEN** 系统遍历所有已知股票
- **AND** 对每只股票，系统从 `StockFinancialRepository` 查询本地最新的 `end_date`
- **AND** 以该 `end_date` 的下一天作为 `start_date`，调用 `fina_indicator` 标准接口拉取新增数据
- **AND** 如果本地无数据（`end_date` 为 None），则拉取该股票的全部历史（自动降级为全量）
- **AND** 如果 API 返回空数据（无新增财报），跳过该股票
- **AND** 有新数据时以 `(source, third_code, end_date)` 为冲突键 Upsert 入库到 `stock_financial` 表
- **AND** 每只股票独立事务提交

#### Scenario: 增量同步过程中单只股票失败

- **GIVEN** 增量同步正在进行中
- **WHEN** 某只股票的查询或写入失败时
- **THEN** 系统记录错误日志并跳过，继续处理下一只
- **AND** 最终返回汇总结果（`total`、`success_count`、`failure_count`、`synced_count`）

---

### Non-Functional Requirements

#### Requirement: 数据冲突处理策略

系统 MUST 使用 Upsert 策略处理数据冲突，以 `(source, third_code, end_date)` 为唯一冲突键，数据存储到 `stock_financial` 表。

- **WHEN** 同一股票同一报告期的财务指标已存在于 `stock_financial` 数据库中
- **AND** 新数据被写入时
- **THEN** 旧记录无条件被最新数据覆盖（包括 `ann_date` 字段的更新）
- **AND** `updated_at` 时间戳和 `version` 乐观锁版本号同步更新

#### Requirement: API 频控遵从

所有对 Tushare API 的调用 MUST 通过 `TokenBucket` 限流器，确保不超过 200次/分钟的频控限制。

#### Requirement: 可观测性

- 全量/增量同步 MUST 以 `structlog` 记录每只股票的同步开始、完成（含记录数）或失败。
- 同步完成后 MUST 输出汇总日志：总股票数、成功数、失败数、总记录数。

#### Requirement: 事务边界

- **全量同步**: 每只股票独立一个事务。一只股票的 upsert 失败不应影响其他股票。
- **单股票同步**: 单个事务。
- **增量同步**: 每只股票独立一个事务。

---

## ADDED Requirements

### Requirement: 财务指标数据包含 symbol 字段

`stock_financial` 表中的每条记录 SHALL 包含 symbol 字段，用于存储股票的标准代码标识符。

#### Scenario: 同步数据包含 symbol
- **WHEN** 系统同步财务指标数据时
- **THEN** 每条记录都包含 symbol 字段，该字段位于 third_code 字段之后

#### Scenario: symbol 字段可为空
- **WHEN** 外部数据源未提供 symbol 信息时
- **THEN** symbol 字段设置为 NULL，不影响数据同步流程

### Requirement: StockFinancial 实体和映射器支持 symbol 字段

系统 SHALL 使用 StockFinancial 实体和对应的映射器处理财务指标数据，支持 symbol 字段。

#### Scenario: 实体包含 symbol 字段
- **WHEN** 创建 StockFinancial 实体时
- **THEN** 该实体包含 symbol 字段，位于 third_code 字段之后

#### Scenario: 映射器处理 symbol 字段
- **WHEN** 使用 StockFinancialPersistenceMapper 时
- **THEN** 映射器正确处理 symbol 字段的数据库映射
