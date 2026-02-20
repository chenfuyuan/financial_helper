# Spec: 股票日线行情数据同步 (stock-daily-sync)

从 TuShare 获取 A 股股票日线行情数据，封装 daily、adj_factor、daily_basic 三个接口并组装成完整的 StockDaily 实体，支持历史数据同步（含断点续传）和增量同步两种模式。

## Purpose

提供股票日线行情数据的完整同步功能，包括历史数据批量同步和日常增量同步，确保数据的完整性、一致性和可追溯性。

## Requirements

### Requirement: 历史数据同步可由 HTTP 触发

系统 SHALL 提供管理端接口，允许调用方通过 HTTP POST 触发股票日线历史数据同步。

#### Scenario: 调用历史同步接口
- **WHEN** 客户端向 `POST /data-engineering/stock-daily/sync/history` 发起请求
- **THEN** 系统执行历史同步用例（遍历股票列表，按断点续传策略同步每只股票的日线数据），并在完成后返回响应

#### Scenario: 历史同步支持指定股票列表
- **WHEN** 客户端调用历史同步接口并在请求体中提供股票代码列表 `ts_codes`
- **THEN** 系统仅同步指定的股票，不同步其他股票

#### Scenario: 历史同步不指定股票列表则同步所有已上市股票
- **WHEN** 客户端调用历史同步接口未提供 `ts_codes`
- **THEN** 系统从 `StockBasicRepository` 查询全部已上市股票并遍历同步

### Requirement: 历史同步支持断点续传

系统 SHALL 在历史同步每只股票前，查询本地已有的最新交易日期，仅拉取增量数据，避免重复同步。

#### Scenario: 首次同步从上市日期开始
- **WHEN** 本地无该股票的任何日线记录
- **THEN** 系统从该股票的上市日期（`list_date`）开始同步至今天

#### Scenario: 非首次同步从断点继续
- **WHEN** 本地已有该股票的日线记录，最新 `trade_date` 为 D
- **THEN** 系统从 D+1 日开始同步至今天

#### Scenario: 已是最新则跳过
- **WHEN** 本地已有该股票的日线记录，最新 `trade_date` ≥ 今天
- **THEN** 系统跳过该股票，不调用网关

### Requirement: 增量同步可由 HTTP 触发

系统 SHALL 提供管理端接口，允许调用方通过 HTTP POST 触发股票日线增量同步。

#### Scenario: 调用增量同步接口
- **WHEN** 客户端向 `POST /data-engineering/stock-daily/sync/increment` 发起请求
- **THEN** 系统执行增量同步用例（按日期获取所有股票的日线数据），并在完成后返回响应

#### Scenario: 增量同步支持指定交易日期
- **WHEN** 客户端调用增量同步接口并在请求体中提供 `trade_date`
- **THEN** 系统同步指定日期的股票日线数据

#### Scenario: 增量同步默认使用昨天自然日
- **WHEN** 客户端调用增量同步接口未提供 `trade_date`
- **THEN** 系统默认使用昨天自然日（`date.today() - timedelta(days=1)`）作为交易日期；若该日非交易日则 TuShare 返回空数据，系统正常返回 `synced_count=0`

### Requirement: 失败记录重试可由 HTTP 触发

系统 SHALL 提供管理端接口，允许调用方通过 HTTP POST 触发重试历史同步失败的记录。

#### Scenario: 调用重试失败记录接口
- **WHEN** 客户端向 `POST /data-engineering/stock-daily/sync/retry-failures` 发起请求
- **THEN** 系统查询所有未解决且未超过最大重试次数的失败记录并逐个重试，成功的标记为已解决

#### Scenario: 支持指定最大重试次数
- **WHEN** 客户端在请求体中提供 `max_retries`（默认 3）
- **THEN** 系统仅重试 `retry_count < max_retries` 的失败记录

#### Scenario: 超过最大重试次数的记录不再自动重试
- **WHEN** 某条失败记录的 `retry_count` ≥ `max_retries`
- **THEN** 系统跳过该记录，不尝试重试

### Requirement: 成功时返回同步结果摘要

同步成功完成后，系统 SHALL 在响应中返回本次同步的摘要信息。

#### Scenario: 历史同步成功返回摘要
- **WHEN** 历史同步执行完成
- **THEN** 客户端收到的成功响应中 MUST 包含：总股票数（`total`）、成功数（`success_count`）、失败数（`failure_count`）、同步总天数（`synced_days`）、耗时（`duration_ms`）

#### Scenario: 增量同步成功返回摘要
- **WHEN** 增量同步执行成功
- **THEN** 客户端收到的成功响应中 MUST 包含：交易日期（`trade_date`）、同步股票数量（`synced_count`）、耗时（`duration_ms`）

#### Scenario: 重试失败记录返回摘要
- **WHEN** 重试失败记录执行完成
- **THEN** 客户端收到的成功响应中 MUST 包含：总处理数（`total`）、解决数（`resolved_count`）、仍失败数（`still_failed_count`）、耗时（`duration_ms`）

### Requirement: 网关为独立抽象接口，统一封装三个 TuShare 接口

系统 SHALL 定义 `StockDailyGateway` 作为独立的抽象接口（不扩展 `StockGateway`），封装 TuShare 的 daily、adj_factor、daily_basic 三个接口并组装数据。接口参数使用领域类型 `date`。

#### Scenario: 网关获取单只股票日线数据
- **WHEN** 应用层调用网关的 `fetch_stock_daily(ts_code, start_date: date, end_date: date)` 方法
- **THEN** 网关内部依次调用 TuShare 的 daily、adj_factor、daily_basic 三个接口，按 `trade_date` 组装数据后返回完整的 `StockDaily` 列表

#### Scenario: 网关获取某一天所有股票日线数据
- **WHEN** 应用层调用网关的 `fetch_daily_all_by_date(trade_date: date)` 方法
- **THEN** 网关按日期获取所有股票的日线数据并组装后返回；若 TuShare 单次返回达到上限，网关内部处理分页直至数据完整

#### Scenario: 任一接口失败则整体失败
- **WHEN** 网关调用 TuShare 三个接口中的任一接口失败（网络错误、解析失败等）
- **THEN** 网关抛出 `ExternalStockServiceError`，不返回部分结果

#### Scenario: daily_basic 部分字段允许为空
- **WHEN** TuShare daily_basic 返回的数据中某些字段为 None（新股/停牌股）
- **THEN** 网关正常组装，对应的 `StockDaily` 实体中这些字段为 `None`，不视为错误

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

系统 SHALL 持久化的股票日线数据记录。ORM 模型包含审计字段（id、created_at、updated_at、version）；领域实体仅包含 id 和以下业务字段：source、third_code、trade_date、open、high、low、close、pre_close、change、pct_chg、vol、amount、adj_factor。daily_basic 字段允许为 NULL：turnover_rate、turnover_rate_f、volume_ratio、pe、pe_ttm、pb、ps、ps_ttm、dv_ratio、dv_ttm、total_share、float_share、free_share、total_mv、circ_mv。

#### Scenario: 成功同步后记录可查且字段完整
- **WHEN** 同步成功完成
- **THEN** 本地可查询到对应记录，且该记录包含所有约定的审计字段和业务字段

#### Scenario: daily_basic 字段为 NULL 时记录仍可正常持久化
- **WHEN** 某条 `StockDaily` 的 daily_basic 字段部分为 None
- **THEN** 该记录仍可正常 upsert，NULL 字段在数据库中存储为 NULL

### Requirement: 历史同步单只股票失败不阻塞且记录失败

历史数据同步时，单只股票同步失败 SHALL 不阻塞其他股票的同步，失败信息 SHALL 记录到失败表中。

#### Scenario: 单只股票失败记录到失败表
- **WHEN** 历史同步过程中某只股票同步失败
- **THEN** 该股票的失败信息（source、third_code、start_date、end_date、错误信息、失败时间、retry_count=0、resolved=false）被记录到 `stock_daily_sync_failure` 表，系统继续同步下一只股票

#### Scenario: 每只股票独立事务
- **WHEN** 历史同步过程中
- **THEN** 每只股票的同步使用独立的数据库事务，单只股票失败不影响其他股票的提交

### Requirement: 增量同步整体事务单只失败即整体失败

增量同步时，所有股票的同步 SHALL 使用整体事务，任一只股票失败 SHALL 导致整体同步失败并回滚。

#### Scenario: 增量同步整体事务
- **WHEN** 增量同步执行过程中
- **THEN** 所有股票的数据在同一个数据库事务中提交，全部成功才提交，任一失败则回滚

### Requirement: TuShare API 调用限流控制

系统 SHALL 控制 TuShare API 调用频率不超过每分钟 200 次，通过 Gateway 实现类内部的 Token Bucket 机制实现。

#### Scenario: API 调用频率控制
- **WHEN** 网关调用 TuShare API
- **THEN** Gateway 内 Token Bucket（容量 200，每分钟补充 200）确保 API 调用频率不超过每分钟 200 次；若 token 不足则等待直至 token 可用

### Requirement: 失败记录表记录失败信息

系统 SHALL 创建 `stock_daily_sync_failure` 表记录历史同步失败的股票信息，包含日期范围以支持精确重试。

#### Scenario: 失败记录包含必要字段
- **WHEN** 某只股票历史同步失败
- **THEN** 失败记录表中创建一条记录，包含 source、third_code、start_date、end_date、error_message、failed_at、retry_count、resolved 字段

#### Scenario: 重试成功标记为已解决
- **WHEN** 失败的股票重试同步成功
- **THEN** 失败记录表中该记录的 `resolved` 字段标记为 true

#### Scenario: 重试失败递增重试次数
- **WHEN** 失败的股票重试同步再次失败
- **THEN** 失败记录表中该记录的 `retry_count` 字段递增，`error_message` 更新为最新错误信息

### Requirement: 仓储支持查询最新交易日期

`StockDailyRepository` SHALL 提供 `get_latest_trade_date(source, third_code)` 方法，返回某只股票本地已有的最新交易日期，用于断点续传。

#### Scenario: 有记录时返回最新日期
- **WHEN** 本地存在该股票的日线记录
- **THEN** 返回最新的 `trade_date`

#### Scenario: 无记录时返回 None
- **WHEN** 本地不存在该股票的任何日线记录
- **THEN** 返回 `None`
