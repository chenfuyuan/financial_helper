## Context

**项目背景：**
- 金融助手系统基于 DDD + 整洁架构，技术栈为 Python 3.11, FastAPI, SQLAlchemy (async), PostgreSQL
- 已有 data_engineering 模块负责股票数据同步，但缺少定时调度机制
- 需要引入调度器支持每天收盘后自动执行数据同步任务

**当前状态：**
- 项目采用四层架构：`interfaces → application → domain ← infrastructure`
- 已有 shared_kernel 提供跨模块共享构建块（Mediator、UoW、Repository 等）
- 已有 `shared_kernel/infrastructure/scheduler.py` 占位（当前为空），预期放置 Scheduler 抽象
- 无调度器相关实现，任务需要手动触发
- 现有 Handler 通过 Router 的 `Depends()` 注入（request-scoped session），不走 Mediator 分发

**关键约束：**
- foundation 作为基础设施层，不能依赖具体业务模块
- 业务模块只能通过 foundation 的 application 层使用调度器
- 需要支持详细日志记录和错误告警，但不自动重试
- 单机部署场景，不需要分布式调度
- 定时任务无 HTTP Request 上下文，需要独立管理 Session/UoW 生命周期

**利益相关者：**
- 开发团队：需要清晰的模块边界和依赖方向
- 运维团队：需要详细的日志和错误信息以便排查问题
- 数据团队：需要可靠的定时任务执行保证数据及时性

## Goals / Non-Goals

**Goals:**
- 提供轻量级定时任务调度器，支持 cron 表达式触发
- 实现 foundation 模块的三层结构（application/infrastructure/interfaces）
- 建立模块注册机制，业务模块主动注册任务，foundation 不依赖具体模块
- 提供详细的结构化日志记录（任务开始/成功/失败/耗时）
- 失败后记录错误日志并告警，不自动重试
- 预留持久化接口，未来可切换到数据库 Job Store
- 定时任务自行管理 Session/UoW 生命周期（独立于 HTTP 请求）

**Non-Goals:**
- 不支持任务自动重试（避免脏数据，由人工确认补执行）
- 不支持分布式调度（当前为单机部署）
- 不支持动态任务管理（任务在代码中定义，启动时注册）
- 不提供任务执行历史持久化（日志已足够）
- 不提供 Web UI 或可视化监控（通过日志查询）
- 不通过 Mediator 分发任务（任务直接构造 Handler，避免 Mediator 与 session 管理的耦合）

## Decisions

### 1. 调度器选型：APScheduler vs Celery Beat

**决策：** 选择 APScheduler（AsyncIOScheduler）

**理由：**
- 项目已有 Redis/Neo4j/InfluxDB 等多个中间件，增加 Celery 会提升复杂度
- APScheduler 支持 async，与 FastAPI 的 asyncio 生态兼容性好
- 定时任务（如每日 16:00 同步数据）重启后重新注册即可，不需要持久化状态
- 轻量级，无需额外中间件

**替代方案：**
- Celery Beat + Redis/RabbitMQ：适合分布式场景，但架构复杂度高
- Airflow：适合复杂数据管道，过于重量级

### 2. 持久化策略：内存 Job Store vs 数据库 Job Store

**决策：** 使用内存 Job Store，不持久化

**理由：**
- 任务是静态的（代码中定义），启动时重新注册
- 不需要记住"上次什么时候执行过"
- 即使今天漏执行了，明天也会继续执行
- 预留接口，未来可通过修改 `AsyncIOSchedulerImpl.__init__()` 切换到 SQLAlchemyJobStore

**替代方案：**
- SQLAlchemyJobStore：适合动态任务或分布式场景，当前不需要

### 3. 依赖方向：模块主动注册 vs foundation 主动 import

**决策：** 业务模块主动注册到 ModuleRegistry

**理由：**
- foundation 作为基础设施层，不能依赖具体业务模块
- 符合依赖倒置原则：foundation 定义抽象接口，业务模块实现并注册
- 符合现有架构风格（类似 FastAPI 的 router 注册机制）
- 显式优于隐式：所有注册在 `app/modules/__init__.py` 中一目了然

**替代方案：**
- foundation 主动 import 业务模块：违反依赖方向约束
- 动态导入扫描：运行时错误，IDE 无法检查

### 4. 错误处理：不自动重试 vs 自动重试

**决策：** 失败后记录日志，不自动重试

**理由：**
- 数据同步任务失败可能是数据质量问题，重试可能导致脏数据
- 需要人工判断是否需要补执行，避免自动化带来的风险
- 通过详细日志（参数、异常、堆栈），运维人员可以快速定位问题

**替代方案：**
- 自动重试 2-3 次：适合网络波动等临时故障，但可能掩盖数据质量问题

### 5. 任务注册：手动注册 vs 装饰器自动发现

**决策：** 手动注册

**理由：**
- 显式优于隐式：所有注册在 `app/modules/__init__.py` 中清晰可见
- 类型安全：IDE 可以自动补全和检查
- 错误提前发现：编译期就能发现导入错误
- 符合现有架构风格

**替代方案：**
- 装饰器 + 扫描机制：增加复杂度，运行时错误，难以调试

### 6. 日志策略：详细结构化日志

**决策：** 使用 structlog 记录详细结构化日志

**理由：**
- 项目已使用 structlog 作为统一日志框架
- 结构化日志便于查询、聚合和告警
- 任务开始/成功/失败均有日志，带任务 ID、模块名等上下文

**日志内容：**
- 任务开始：task_id, task_name, module
- 任务成功：task_id, task_name, module, duration_ms
- 任务失败：task_id, task_name, module, exception, traceback, duration_ms

### 7. 定时任务的 Session/UoW 生命周期管理

**决策：** 任务执行函数自行创建 session 和 UoW，通过 `Database.session_factory` 构建独立于 HTTP 请求的 session

**理由：**
- 定时任务在 APScheduler 协程中执行，没有 FastAPI Request 上下文，无法使用 `Depends(get_uow)`
- 当前 Handler（如 `SyncStockDailyIncrementHandler`）需要 `gateway`, `repository`, `uow` 等依赖
- 任务执行函数直接构造 Handler 并调用 `handler.handle(command)`，**不通过 Mediator 分发**（Mediator 当前未注册 handler factory，且 handler 需要 request-scoped session）
- Session 在任务函数内创建和关闭，确保资源不泄漏

**替代方案：**
- 通过 Mediator 分发：需要在 Mediator 中注册 handler factory，且 factory 需自行管理 session。增加复杂度，收益不大。未来有需求时可迁移。

### 8. 任务工厂签名：直接返回 async callable

**决策：** 任务工厂直接返回 `Callable[[], Awaitable[None]]`（async callable），不做多层嵌套

**理由：**
- 原设计中「工厂返回工厂」的双层嵌套导致 `await task_callable()` 类型不匹配
- 简化为：工厂函数接收依赖（`session_factory`, `settings`），返回 async callable，调度器直接 await 即可
- 减少认知复杂度，类型安全

## Risks / Trade-offs

**[风险 1] 单机调度器的单点故障**
- **描述：** 进程重启期间错过的任务不会自动补执行（除非在 misfire_grace_time 内）
- **缓解：** 所有任务默认 `misfire_grace_time=7200`（2 小时），允许重启后补执行；运维人员可通过日志发现并手动触发

**[风险 2] 不自动重试可能漏执行**
- **描述：** 临时故障（如网络波动）导致任务失败，不会自动重试
- **缓解：** 通过详细日志快速定位问题；提供手动触发 API 补执行；大部分临时故障可在 misfire_grace_time 内自动恢复

**[风险 3] 手动注册容易遗漏**
- **描述：** 新增模块时可能忘记在 `app/modules/__init__.py` 中注册
- **缓解：** 在架构测试中添加检查用例；代码审查时重点关注；文档中明确说明注册步骤

**[风险 4] 任务执行时间过长导致重叠**
- **描述：** 若任务执行时间超过调度间隔，可能导致多个实例同时运行
- **缓解：** 设置 `max_instances=1` 防止任务重叠；设置 `coalesce=True` 合并错过的执行

**[风险 5] 未来迁移到分布式调度需要改造**
- **描述：** 当前设计针对单机场景，未来多实例部署需要切换到 Celery
- **缓解：** 通过 Scheduler Protocol 抽象接口，未来只需替换实现；任务注册机制保持不变

**[风险 6] import-linter 配置需同步更新**
- **描述：** 新增 `app.foundation` 顶级模块，但现有 import-linter 的 `containers` 配置中未包含该模块
- **缓解：** 在 `pyproject.toml` 的 `[tool.importlinter]` 中追加 `app.foundation` 到 containers；并新增 forbidden contract 确保 foundation 不依赖业务模块

## Migration Plan

**部署步骤：**
1. 添加 APScheduler 依赖到 `pyproject.toml`
2. 更新 `pyproject.toml` 的 import-linter 配置（containers + forbidden contract）
3. 创建 foundation 调度器模块（application/infrastructure/interfaces），含 `__init__.py`
4. 创建 ModuleRegistry 注册机制
5. 创建 data_engineering 模块的任务定义（`interfaces/schedulers/tasks.py`）
6. 扩展 `app/modules/__init__.py` 注册所有模块任务
7. 扩展 `interfaces/main.py` 的 lifespan 初始化调度器
8. 编写单元测试和架构测试
9. 运行 `make ci` 验证
10. 部署到生产环境

**回滚策略：**
- 若调度器启动失败：注释掉 `main.py` 中的调度器初始化代码，应用仍可正常运行
- 若任务执行异常：通过日志定位问题模块，临时注释掉该模块的任务注册
- 不影响现有功能：调度器是新增功能，回滚不会影响已有业务

## Open Questions

- **是否需要提供任务执行历史查询接口？** 当前通过日志查询，未来若需要持久化执行历史，可考虑添加到数据库
- **是否需要支持任务依赖关系？** 当前任务独立执行，未来若需要任务链（如 A 执行完再执行 B），可考虑引入 LangGraph 或自定义状态机
- **是否需要支持动态启用/禁用任务？** 当前任务启动后一直运行，未来若需要运行时控制，可通过扩展 ModuleRegistry 提供管理接口
- **未来是否迁移到 Mediator 分发？** 当前任务直接构造 Handler，未来若 Mediator 支持 scope-aware handler factory，可考虑迁移
