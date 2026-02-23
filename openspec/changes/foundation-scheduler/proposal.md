## Why

当前项目缺少统一的定时任务调度机制，各业务模块（如 data_engineering 的股票数据同步）无法按时自动执行。需要引入轻量级调度器，支持 cron 表达式触发、详细日志记录和错误告警，满足金融数据定时同步的需求。

## What Changes

- **新增 foundation 调度器模块**：提供 Scheduler 抽象接口和基于 APScheduler 的实现
- **新增模块注册机制**：ModuleRegistry 允许业务模块主动注册定时任务，foundation 不依赖具体业务模块
- **新增依赖注入**：通过 `get_scheduler()` 在 interfaces 层注入调度器实例
- **扩展应用生命周期**：在 `main.py` 的 lifespan 中初始化、启动和关闭调度器
- **新增业务模块任务定义**：业务模块在 `interfaces/schedulers/` 目录定义任务配置和工厂函数
- **添加 APScheduler 依赖**：在 `pyproject.toml` 中添加 `APScheduler>=3.10.0`

## Capabilities

### New Capabilities

- `foundation-scheduler`: foundation 模块的调度器核心能力，包括 Scheduler Protocol、CronTrigger、ScheduledTaskConfig 和 AsyncIOSchedulerImpl 实现
- `foundation-module-registry`: 模块任务注册机制，允许业务模块主动注册定时任务，foundation 不主动依赖业务模块
- `data-engineering-scheduled-tasks`: data_engineering 模块的定时任务定义，包括股票日线数据同步等任务的配置和工厂函数

### Modified Capabilities

- `application-lifespan`: 扩展 FastAPI 应用的生命周期管理，增加调度器的初始化、任务注册和关闭流程

## Impact

- **依赖增加**：需要添加 APScheduler 库
- **架构调整**：新增 foundation 模块的三层结构（application/infrastructure/interfaces）
- **模块注册扩展**：`app/modules/__init__.py` 需要新增模块注册中心，统一管理业务模块的组件注册
- **生命周期扩展**：`interfaces/main.py` 的 lifespan 需要增加调度器相关逻辑
- **错误处理策略**：任务失败时记录详细日志但不自动重试，需要运维人员手动确认补执行
- **日志系统**：所有任务执行过程通过 structlog 记录结构化日志，便于查询和告警
