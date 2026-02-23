## ADDED Requirements

### Requirement: 调度器提供抽象接口

系统 SHALL 提供 Scheduler Protocol，定义调度器的基本操作契约，包括添加任务、启动和关闭调度器。

#### Scenario: 定义调度器接口
- **WHEN** 开发者导入 `app.foundation.application.scheduler.Scheduler`
- **THEN** 可以使用该 Protocol 作为类型注解，确保依赖注入的调度器实例符合接口规范

### Requirement: CronTrigger 为 frozen dataclass 值对象

系统 SHALL 提供 `@dataclass(frozen=True)` 的 CronTrigger 类，支持通过 cron 字段配置任务执行时间，包括小时、分钟、秒、星期几、日期和月份，并在 `__post_init__` 中校验字段范围。

#### Scenario: 配置每天固定时间执行
- **WHEN** 创建 `CronTrigger(hour=16, minute=30)`
- **THEN** 任务将在每天 16:30 执行，second 默认为 0

#### Scenario: 配置每周固定时间执行
- **WHEN** 创建 `CronTrigger(hour=9, minute=0, day_of_week='mon')`
- **THEN** 任务将在每周一 9:00 执行

#### Scenario: 非法参数提前报错
- **WHEN** 创建 `CronTrigger(hour=25)` 或 `CronTrigger(minute=60)`
- **THEN** `__post_init__` 抛出 `ValueError`，提前暴露配置错误

### Requirement: 调度器支持任务配置

系统 SHALL 提供 `@dataclass(frozen=True)` 的 ScheduledTaskConfig 数据类，包含任务 ID、触发器、名称、所属模块、最大并发数、错过执行合并策略和补执行时间窗口（默认 7200 秒）。

#### Scenario: 创建任务配置
- **WHEN** 创建 `ScheduledTaskConfig(id='de.sync_stock_daily_increment', trigger=trigger, name='同步股票日线', module='data_engineering')`
- **THEN** 配置对象包含所有必要信息，`misfire_grace_time` 默认为 7200（2 小时）

### Requirement: 调度器实现基于 APScheduler

系统 SHALL 提供 AsyncIOSchedulerImpl 类，基于 APScheduler 的 AsyncIOScheduler 实现 Scheduler Protocol。

#### Scenario: 初始化调度器
- **WHEN** 创建 `AsyncIOSchedulerImpl()` 实例
- **THEN** 内部创建 AsyncIOScheduler 实例，使用内存 Job Store

#### Scenario: 添加定时任务
- **WHEN** 调用 `scheduler.add_job(config, task_callable)`，其中 `task_callable` 是 async callable
- **THEN** 任务被注册到 APScheduler，包含 wrapped_task 包装函数用于日志记录和耗时统计

#### Scenario: 启动调度器
- **WHEN** 调用 `scheduler.start()`
- **THEN** APScheduler 开始运行，按时触发已注册的任务

#### Scenario: 关闭调度器
- **WHEN** 调用 `scheduler.shutdown(wait=True)`
- **THEN** APScheduler 停止运行，等待正在执行的任务完成

### Requirement: 任务执行记录详细日志

系统 SHALL 在任务执行前、执行成功和执行失败时记录详细的结构化日志，包括任务 ID、任务名称、所属模块、耗时和异常信息。

#### Scenario: 任务开始执行
- **WHEN** 任务开始执行
- **THEN** 记录 info 级别日志，包含 task_id、task_name、module 字段

#### Scenario: 任务执行成功
- **WHEN** 任务执行完成且未抛出异常
- **THEN** 记录 info 级别日志，包含 task_id、task_name、module、duration_ms 字段

#### Scenario: 任务执行失败
- **WHEN** 任务执行过程中抛出异常
- **THEN** 记录 error 级别日志，包含 task_id、task_name、module、duration_ms 字段及 exc_info=True，并重新抛出异常

### Requirement: 任务支持防重叠执行

系统 SHALL 支持配置 `max_instances=1`，防止同一任务的多个实例同时运行。

#### Scenario: 防止任务重叠
- **WHEN** 任务配置 `max_instances=1` 且任务执行时间超过调度间隔
- **THEN** 调度器不会启动新的任务实例，直到当前实例完成

### Requirement: 任务支持错过执行合并

系统 SHALL 支持配置 `coalesce=True`，将错过的多次执行合并为一次。

#### Scenario: 合并错过的执行
- **WHEN** 调度器停止期间错过了多次任务执行时间
- **THEN** 启动后只执行一次，而不是执行所有错过的次数

### Requirement: 任务支持补执行时间窗口

系统 SHALL 支持配置 `misfire_grace_time`（默认 7200 秒），允许在错过执行后的一定时间窗口内补执行。

#### Scenario: 补执行错过的任务
- **WHEN** 任务错过执行时间但在 misfire_grace_time（默认 7200 秒 = 2 小时）内
- **THEN** 调度器会触发补执行

#### Scenario: 超过补执行窗口
- **WHEN** 任务错过执行时间且超过 misfire_grace_time
- **THEN** 调度器不再补执行该次任务

### Requirement: 调度器支持依赖注入

系统 SHALL 提供 `get_scheduler()` 函数，返回 `Scheduler` Protocol 类型（不暴露具体实现），用于在 FastAPI 的 interfaces 层通过依赖注入获取调度器实例。

#### Scenario: 依赖注入调度器
- **WHEN** Router 或 Consumer 需要访问调度器
- **THEN** 可以通过 `Depends(get_scheduler)` 注入 `Scheduler` Protocol 类型的调度器实例
