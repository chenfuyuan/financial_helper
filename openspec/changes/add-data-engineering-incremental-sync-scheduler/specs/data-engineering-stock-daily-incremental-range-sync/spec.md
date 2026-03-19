## ADDED Requirements

### Requirement: 股票日线区间增量同步 MUST 正确计算日期区间

<!-- REASON: 原文标题缺少 RFC 2119 关键词前缀，不符合"所有需求必须用 MUST/SHALL/MAY 开头"的规则。重新措辞使关键词位于句首。 -->

系统 MUST 提供 `SyncStockDailyIncrementRange` 指令，根据已有的 Tushare 股票日线数据和可选的 `end_date` 参数来确定需要同步的日期区间。
当未指定 `end_date` 时，该指令 MUST 将 `today - 1 day` 视为默认的 `end_date`。
当数据库中不存在任何 Tushare 股票日线数据时，系统 MUST 使用 `2010-01-01` 作为 `start_date`。
当数据库中已存在 Tushare 股票日线数据时，系统 MUST 计算 `start_date = latest_trade_date + 1 day`，其中 `latest_trade_date` 是 `source = TUSHARE` 条件下全局最大的 `trade_date`。
当计算得到的 `start_date` 晚于 `end_date` 时，系统 MUST 不执行任何同步操作，并 MUST 返回同步天数和记录数均为 0 的结果。

<!-- REASON: 所有 Scenario 统一补充 GIVEN（前置条件），使三段式 Given/When/Then 完整，提升可读性和测试可映射性。 -->

#### Scenario: 没有历史数据时使用固定历史起始日期
- **GIVEN** 数据库中不存在任何 `source = TUSHARE` 的股票日线数据
- **WHEN** 执行 `SyncStockDailyIncrementRange` 指令且未显式指定 `end_date`
- **THEN** 系统 MUST 计算 `start_date = 2010-01-01`
  AND `end_date = today - 1 day`
  AND MUST 报告从 `2010-01-01` 到 `today - 1 day` 的日期区间

#### Scenario: 已有数据时从最新交易日加一开始
- **GIVEN** `source = TUSHARE` 条件下全局最大的 `trade_date` 为 `2024-12-31`
- **WHEN** 执行 `SyncStockDailyIncrementRange` 指令且未显式指定 `end_date`
- **THEN** 系统 MUST 计算 `start_date = 2025-01-01`
  AND `end_date = today - 1 day`
  AND MUST 报告从 `2025-01-01` 到 `today - 1 day` 的日期区间

#### Scenario: 使用不晚于今天的自定义结束日期
- **GIVEN** 数据库中已存在 Tushare 日线数据
- **WHEN** 执行 `SyncStockDailyIncrementRange` 指令，并显式传入一个不晚于 `today` 的 `end_date`
- **THEN** 系统 MUST 使用该显式的 `end_date`，而不是 `today - 1 day`
  AND MUST 仍然按照是否存在历史数据的规则计算 `start_date`

#### Scenario: 起始日期晚于结束日期时不执行任何同步
- **GIVEN** 数据库中 `source = TUSHARE` 的最大 `trade_date` 为 `2025-03-18`
- **WHEN** 执行 `SyncStockDailyIncrementRange`，计算得到 `start_date = 2025-03-19`，而 `end_date = 2025-03-18`
- **THEN** 系统 MUST 不执行任何同步工作
  AND MUST 返回 `synced_days = 0` 且 `synced_records = 0` 的结果

#### Scenario: 起始日期等于结束日期时同步恰好一天

<!-- REASON: 新增边界场景——原文遗漏了 start_date == end_date 的单日边界情况。区间为闭区间 [d, d] 应同步恰好 1 天。 -->

- **GIVEN** 数据库中 `source = TUSHARE` 的最大 `trade_date` 为 `2025-03-17`
- **WHEN** 执行 `SyncStockDailyIncrementRange`，`end_date = 2025-03-18`
- **THEN** 系统 MUST 计算 `start_date = 2025-03-18`
  AND MUST 对 `2025-03-18` 这一天执行同步操作
  AND 结果中 `synced_days` MUST 为 1（若该日同步成功）

---

### Requirement: 股票日线区间增量同步 MUST 校验输入参数

<!-- REASON: 新增需求——原文 spec 完全没有输入校验条款，但 design.md 提及"需校验不晚于 today"。从"魔鬼测试工程师"视角，恶意或误传的未来日期是高概率边界场景。 -->

系统 MUST 对 `SyncStockDailyIncrementRange` 指令的 `end_date` 参数进行校验。
当 `end_date` 晚于 `today` 时，系统 MUST 拒绝执行并抛出校验错误，MUST 不执行任何同步操作。

#### Scenario: end_date 为未来日期时拒绝执行
- **GIVEN** 当前日期为 `2025-03-19`
- **WHEN** 执行 `SyncStockDailyIncrementRange`，传入 `end_date = 2025-04-01`（晚于 `today`）
- **THEN** 系统 MUST 拒绝该指令
  AND MUST 抛出包含明确错误信息的校验异常
  AND MUST 不执行任何同步操作

#### Scenario: end_date 恰好为今天时允许执行
- **GIVEN** 当前日期为 `2025-03-19`
- **WHEN** 执行 `SyncStockDailyIncrementRange`，传入 `end_date = 2025-03-19`（等于 `today`）
- **THEN** 系统 MUST 接受该指令
  AND MUST 使用 `2025-03-19` 作为 `end_date` 正常计算区间并执行同步

---

### Requirement: 股票日线区间增量同步 MUST 按日循环并使用幂等 upsert

<!-- REASON: 在标题中补充 MUST 关键词前缀。 -->

系统 MUST 在计算得到的 `[start_date, end_date]` 闭区间内，按天循环同步对应日期的股票日线数据。
对于区间内的每一天，系统 MUST 通过 `StockDailyGateway.fetch_daily_all_by_date(trade_date)` 从 Tushare 拉取全市场股票日线数据。
对于每一条拉取到的记录，系统 MUST 基于 `DataSource.TUSHARE` 的股票基础信息数据解析并填充 `symbol` 字段。
系统 MUST 通过 `StockDailyRepository.upsert_many` 持久化这些记录，并基于 `(source, third_code, trade_date)` 唯一键保证写入的幂等性。
在相同日期区间上多次执行 `SyncStockDailyIncrementRange` MUST 不得在数据库中产生重复的逻辑记录。
每一天的同步 MUST 使用独立事务（`async with uow`），单日成功后提交，单日失败不回滚其他日期。

#### Scenario: 多天全市场同步成功
- **GIVEN** 数据库中 stock_basic 表包含 Tushare 数据源的完整股票基础信息
- **WHEN** 计算得到的区间为 `2025-01-01` 至 `2025-01-03`
  AND 对于区间内的每一天，Tushare 网关都返回非空的日线数据
- **THEN** 系统 MUST 在区间内每一天各调用一次网关
  AND MUST 为每条记录基于股票基础信息填充 `symbol`
  AND MUST 在每一天分别调用一次 `upsert_many` 写入该日的数据
  AND 数据库中 MUST 仅包含每个 `(source, third_code, trade_date)` 一条逻辑记录

#### Scenario: 非交易日无记录但不视为失败
- **GIVEN** 计算得到的区间中包含一个周末日期（如 `2025-01-04` 星期六）
- **WHEN** Tushare 网关在该日返回空结果集
- **THEN** 系统 MUST 将该日视为一次成功的空操作
  AND MUST 不记录该日为失败
  AND MUST 继续处理区间内后续日期

#### Scenario: 重复执行同一日期区间保持幂等
- **GIVEN** 区间 `[2025-01-01, 2025-01-03]` 已成功同步过一次
- **WHEN** 在相同的 `[2025-01-01, 2025-01-03]` 区间上第二次执行 `SyncStockDailyIncrementRange`
  AND `upsert_many` 基于 `(source, third_code, trade_date)` 冲突进行更新
- **THEN** 第二次执行 MUST 不得增加数据库中股票日线逻辑行的数量
  AND 现有行中的业务字段值 MUST 反映第二次执行后的最新数据

---

### Requirement: 股票日线区间增量同步 MUST 按日期隔离失败

系统 MUST 在执行 `SyncStockDailyIncrementRange` 时，将同步失败按日期进行隔离。
当某一天的同步失败（网关错误、数据库错误或其他异常）时，系统 MUST 记录该失败的 `trade_date` 和错误详情，并 MUST 继续处理区间内剩余日期。
`SyncStockDailyIncrementRange` 的结果对象 MUST 包含以下字段：`start_date: date`、`end_date: date`、`synced_days: int`、`synced_records: int`、`failed_dates: list[date]`。

<!-- REASON: 明确列出 Result 字段名称，消除"暴露一个失败日期列表"的模糊表述，与 design.md 中的 Result 定义对齐。 -->

#### Scenario: 单日失败但后续日期仍被处理
- **GIVEN** 计算得到的区间包含三天 `[2025-01-01, 2025-01-03]`
- **WHEN** 第二天 `2025-01-02` 因网关瞬时错误导致同步失败
- **THEN** 系统 MUST 将 `2025-01-02` 加入结果中的 `failed_dates` 列表
  AND MUST 仍然尝试同步 `2025-01-03` 的数据
  AND 结果中 `synced_days` MUST 为 2，`failed_dates` 长度 MUST 为 1

#### Scenario: 所有日期均失败时全部列入失败列表
- **GIVEN** 区间内包含三天
- **WHEN** 每一天的同步都因网关不可用而失败
- **THEN** 系统 MUST 将区间内所有日期全部加入 `failed_dates` 列表
  AND 结果中 `synced_days` MUST 为 0
  AND 结果中 `synced_records` MUST 为 0

---

### Requirement: 股票日线区间增量同步 MUST 处理网关异常与超时

<!-- REASON: 新增需求——原文仅在"按日期隔离失败"中笼统提及"网关错误"，但缺少对具体异常类型（超时、认证失败、限流）的行为定义。从魔鬼测试工程师视角，网络超时和认证失败是高频异常场景。 -->

当 Tushare 网关调用发生超时（网络不可达或响应时间超过阈值）时，系统 MUST 将该日标记为失败并继续后续日期。
当 Tushare 网关返回认证失败（Token 过期或无效）时，系统 SHALL 终止后续日期的同步循环（fail-fast），因为后续日期大概率也会失败。
<!-- REASON: 这里使用 SHALL 而非 MUST：认证失败 fail-fast 是强烈建议的优化策略，但非所有场景下都是绝对强制的（如 Token 可能在短暂失效后恢复）。 -->
当单日网关调用失败时，系统 MUST 在错误日志中记录 `trade_date`、错误类型和错误详情（含堆栈），日志格式 SHALL 使用结构化键值对。

#### Scenario: 网关请求超时时标记失败并继续
- **GIVEN** 计算得到的区间为 `[2025-01-06, 2025-01-08]`
- **WHEN** `2025-01-07` 的 `fetch_daily_all_by_date` 调用因网络超时抛出 `TimeoutError`
- **THEN** 系统 MUST 将 `2025-01-07` 加入 `failed_dates`
  AND MUST 在 error 日志中记录 `trade_date=2025-01-07` 和超时错误详情
  AND MUST 继续尝试同步 `2025-01-08`

#### Scenario: 网关返回认证失败时终止后续同步
- **GIVEN** 计算得到的区间为 `[2025-01-06, 2025-01-10]`
- **WHEN** `2025-01-06` 的网关调用因 Tushare Token 无效返回认证错误
- **THEN** 系统 SHALL 终止后续日期 `[2025-01-07, 2025-01-10]` 的同步循环
  AND MUST 将 `2025-01-06` 加入 `failed_dates`
  AND MUST 在 error 日志中明确标注认证失败原因

---

### Requirement: 股票日线区间增量同步 SHALL 处理 stock_basic 映射缺失

<!-- REASON: 新增需求——原文 spec 和 design 均依赖 stock_basic 做 third_code → symbol 映射，但未定义映射不完整时的行为。从魔鬼测试工程师视角，stock_basic 数据可能未同步或延迟更新，导致部分 third_code 无法匹配。 -->

当 `StockBasicRepository` 中不存在某个 `third_code` 对应的 `symbol` 时，系统 SHALL 将该记录的 `symbol` 字段置为空或保持原值，MUST 不因映射缺失而跳过该记录的写入。
当 `StockBasicRepository` 返回空集合（无任何 Tushare 数据源的股票基础信息）时，系统 SHALL 记录 warning 级别日志，MAY 继续执行同步（所有记录的 `symbol` 字段均为空），但 MUST 在结果日志中标注 stock_basic 数据缺失。

#### Scenario: 部分 third_code 无法匹配 symbol 时仍正常写入
- **GIVEN** stock_basic 表包含 4,000 只股票的映射信息
  AND Tushare 网关返回的某日日线数据包含 4,200 条记录（含新上市或映射表未收录的股票）
- **WHEN** 200 条记录的 `third_code` 在 stock_basic 中找不到对应 `symbol`
- **THEN** 系统 MUST 仍然将全部 4,200 条记录写入数据库
  AND 未匹配的 200 条记录的 `symbol` 字段 SHALL 为空
  AND 系统 SHALL 在 debug 或 info 日志中记录未匹配的 `third_code` 数量

#### Scenario: stock_basic 数据完全为空时发出警告
- **GIVEN** `StockBasicRepository.find_all(DataSource.TUSHARE)` 返回空列表
- **WHEN** 执行 `SyncStockDailyIncrementRange`
- **THEN** 系统 SHALL 记录 warning 级别日志，标注 stock_basic 映射数据为空
  AND MAY 继续执行同步（所有记录的 `symbol` 均为空）
  AND 结果 MUST 正常返回 `synced_days` 和 `synced_records` 计数

---

### Requirement: 股票日线区间增量同步 MUST 返回结构化结果

<!-- REASON: 新增独立需求——原文将 Result 字段散落在其他 Requirement 中提及，未集中定义。明确 Result 契约有利于上游调用方（调度器、API）一致消费。 -->

`SyncStockDailyIncrementRange` 执行完毕后 MUST 返回一个结构化结果对象，包含以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `start_date` | `date` | 实际补数起始日期 |
| `end_date` | `date` | 实际补数结束日期 |
| `synced_days` | `int` | 成功同步的天数（不含失败天数） |
| `synced_records` | `int` | 成功 upsert 的总记录数 |
| `failed_dates` | `list[date]` | 同步失败的日期列表 |

当 `start_date > end_date`（无需同步）时，结果 MUST 仍然包含所有字段，其中 `synced_days = 0`、`synced_records = 0`、`failed_dates` 为空列表。

#### Scenario: 正常区间同步后返回完整结果
- **GIVEN** 计算得到的区间为 `[2025-01-01, 2025-01-03]`
  AND 三天均同步成功，分别写入 5000、4800、5100 条记录
- **WHEN** 同步执行完毕
- **THEN** 结果中 `start_date` MUST 为 `2025-01-01`
  AND `end_date` MUST 为 `2025-01-03`
  AND `synced_days` MUST 为 3
  AND `synced_records` MUST 为 14900
  AND `failed_dates` MUST 为空列表

#### Scenario: 无需同步时返回零值结果
- **GIVEN** 数据库已同步到 `2025-03-18`
- **WHEN** 执行 `SyncStockDailyIncrementRange`，`end_date = 2025-03-18`，计算得到 `start_date = 2025-03-19 > end_date`
- **THEN** 结果 MUST 包含 `synced_days = 0`、`synced_records = 0`、`failed_dates = []`
