## MODIFIED Requirements

### Requirement: 以 (source, third_code, trade_date) 为唯一键幂等持久化

系统 SHALL 将每条股票日线数据的持久化唯一键定义为 (source, third_code, trade_date)。同一 (source, third_code, trade_date) 的多次同步 SHALL 表现为 upsert：已存在则更新字段，不存在则插入；多次调用后最终持久化状态一致（幂等）。

#### Scenario: 首次同步插入
- **WHEN** 同步执行且某条记录的 (source, third_code, trade_date) 在本地尚不存在
- **THEN** 该条记录被插入本地表

#### Scenario: 再次同步更新
- **WHEN** 同步执行且某条记录的 (source, third_code, trade_date) 在本地已存在
- **THEN** 该条记录对应行被更新（业务字段覆盖、`updated_at` 刷新、`version` 递增），唯一键不变，最终仅保留一行

#### Scenario: 空数据不报错
- **WHEN** 网关返回空列表（如非交易日、新上市股票无历史数据）
- **THEN** 系统正常完成，不插入任何记录，不抛出异常

### Requirement: 持久化记录包含完整字段

系统 SHALL 持久化的股票日线数据记录。ORM 模型包含审计字段（id、created_at、updated_at、version）；领域实体仅包含 id 和以下业务字段：source、third_code、symbol、trade_date、open、high、low、close、pre_close、change、pct_chg、vol、amount、adj_factor。daily_basic 字段允许为 NULL：turnover_rate、turnover_rate_f、volume_ratio、pe、pe_ttm、pb、ps、ps_ttm、dv_ratio、dv_ttm、total_share、float_share、free_share、total_mv、circ_mv。

#### Scenario: 成功同步后记录可查且字段完整
- **WHEN** 同步成功完成
- **THEN** 本地可查询到对应记录，且该记录包含所有约定的审计字段和业务字段，包括 symbol 字段

#### Scenario: daily_basic 字段为 NULL 时记录仍可正常持久化
- **WHEN** 某条 `StockDaily` 的 daily_basic 字段部分为 None
- **THEN** 该记录仍可正常 upsert，NULL 字段在数据库中存储为 NULL

---

## ADDED Requirements

### Requirement: 股票日线数据包含 symbol 字段

`stock_daily` 表中的每条记录 SHALL 包含 symbol 字段，用于存储股票的标准代码标识符。

#### Scenario: 同步数据包含 symbol
- **WHEN** 系统同步股票日线数据时
- **THEN** 每条记录都包含 symbol 字段，该字段位于 third_code 字段之后

#### Scenario: symbol 字段可为空
- **WHEN** 外部数据源未提供 symbol 信息时
- **THEN** symbol 字段设置为 NULL，不影响数据同步流程

### Requirement: StockDaily 实体和映射器支持 symbol 字段

系统 SHALL 使用 StockDaily 实体和对应的映射器处理日线数据，支持 symbol 字段。

#### Scenario: 实体包含 symbol 字段
- **WHEN** 创建 StockDaily 实体时
- **THEN** 该实体包含 symbol 字段，位于 third_code 字段之后

#### Scenario: 映射器处理 symbol 字段
- **WHEN** 使用 StockDailyPersistenceMapper 时
- **THEN** 映射器正确处理 symbol 字段的数据库映射
