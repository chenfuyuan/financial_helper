## ADDED Requirements

### Requirement: data_engineering 模块定义股票日线同步任务

系统 SHALL 在 data_engineering 模块的 `interfaces/schedulers/tasks.py` 中定义股票日线数据增量同步的定时任务配置。

#### Scenario: 配置每天 16:30 执行
- **WHEN** 创建 `ScheduledTaskConfig(id='de.sync_stock_daily_increment', trigger=CronTrigger(hour=16, minute=30), ...)`
- **THEN** 任务将在每天 16:30 执行（收盘后 30 分钟）

### Requirement: 任务配置包含防重叠和补执行策略

系统 SHALL 为股票日线同步任务配置 `max_instances=1`、`coalesce=True` 和 `misfire_grace_time=7200`（2 小时）。

#### Scenario: 防止任务重叠
- **WHEN** 任务执行时间超过 30 分钟
- **THEN** 下一次调度不会启动新实例，直到当前实例完成

#### Scenario: 补执行错过的任务
- **WHEN** 调度器停止后重启
- **THEN** 若错过执行时间在 2 小时（7200 秒）内，会触发补执行

### Requirement: 任务执行函数自行管理 Session 生命周期

系统 SHALL 在 `create_task_callables(session_factory)` 中创建 async callable，每个 callable 自行管理 Session 生命周期：创建 session → 构造 Handler 及其依赖（Gateway、Repository、UoW）→ 执行 command → 关闭 session。不通过 Mediator 分发。

#### Scenario: 创建任务 async callable
- **WHEN** 调用 `create_task_callables(session_factory)`
- **THEN** 返回包含 `de.sync_stock_daily_increment` 键的字典，值为可直接 await 的 async callable

#### Scenario: 任务执行直接构造 Handler
- **WHEN** async callable 被调度器调用
- **THEN** 创建独立 session，构造 `SyncStockDailyIncrementHandler`，调用 `handler.handle(SyncStockDailyIncrement(trade_date=...))`,最终关闭 session（无论成功或失败）

### Requirement: 任务提供配置和 callable 接口

系统 SHALL 提供 `get_scheduled_tasks()` 和 `create_task_callables()` 函数，供模块注册使用。

#### Scenario: 获取任务配置列表
- **WHEN** 调用 `get_scheduled_tasks()`
- **THEN** 返回包含所有任务配置的列表

#### Scenario: 创建任务 callable 映射
- **WHEN** 调用 `create_task_callables(session_factory)`
- **THEN** 返回任务 ID 到 async callable 的映射字典

### Requirement: 模块提供统一的入口函数

系统 SHALL 在 `interfaces/schedulers/__init__.py` 中提供 `create_scheduled_tasks(session_factory)` 函数，返回符合 ModuleRegistry 要求的 `(configs, task_callables)` 元组。

#### Scenario: 创建模块级任务入口
- **WHEN** 调用 `create_scheduled_tasks(session_factory)`
- **THEN** 返回 `(list[ScheduledTaskConfig], dict[str, Callable[[], Awaitable[None]]])` 元组

### Requirement: 任务执行记录详细日志

系统 SHALL 通过 foundation 调度器的 wrapped_task 包装函数，自动记录任务执行的详细日志（含耗时）。

#### Scenario: 任务执行日志
- **WHEN** 任务开始执行、执行成功或执行失败
- **THEN** 调度器自动记录结构化日志，包含 task_id='de.sync_stock_daily_increment'、module='data_engineering'、duration_ms 等字段

### Requirement: 任务失败不自动重试

系统 SHALL 确保股票日线同步任务失败时不自动重试，而是记录错误日志并抛出异常。

#### Scenario: 任务失败处理
- **WHEN** 任务执行过程中发生异常（如 Tushare 接口调用失败）
- **THEN** 记录 error 级别日志（含 exc_info=True）并重新抛出异常，不自动重试
