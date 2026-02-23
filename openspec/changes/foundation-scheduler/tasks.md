## 1. 项目配置与依赖

- [ ] 1.1 在 `pyproject.toml` 中添加 APScheduler 依赖
- [ ] 1.2 在 `pyproject.toml` 中更新 import-linter 配置（containers 追加 `app.foundation`）
- [ ] 1.3 在 `pyproject.toml` 中添加 forbidden contract 确保 foundation 不依赖业务模块

## 2. CronTrigger 值对象（TDD）

- [ ] 2.1 **[RED]** 编写 `test_cron_trigger_default_values.py`：验证 `CronTrigger(hour=16, minute=30)` 的 second 默认为 0
- [ ] 2.2 **[GREEN]** 实现 CronTrigger frozen dataclass，包含 second 默认值
- [ ] 2.3 **[RED]** 编写 `test_cron_trigger_validation.py`：验证 `CronTrigger(hour=25)` 抛出 ValueError
- [ ] 2.4 **[GREEN]** 在 `__post_init__` 中添加小时范围校验（0-23）
- [ ] 2.5 **[RED]** 编写测试：验证 `CronTrigger(minute=60)` 抛出 ValueError
- [ ] 2.6 **[GREEN]** 在 `__post_init__` 中添加分钟范围校验（0-59）
- [ ] 2.7 **[REFACTOR]** 提取公共校验逻辑到 `_validate_range()` 辅助函数
- [ ] 2.8 **[RED]** 编写测试：验证 `CronTrigger(day_of_week='mon')` 正确存储
- [ ] 2.9 **[GREEN]** 添加 day_of_week、month、day 字段支持

## 3. ScheduledTaskConfig 配置类（TDD）

- [ ] 3.1 **[RED]** 编写 `test_scheduled_task_config.py`：验证创建配置对象包含所有必填字段
- [ ] 3.2 **[GREEN]** 实现 ScheduledTaskConfig frozen dataclass
- [ ] 3.3 **[RED]** 编写测试：验证 `misfire_grace_time` 默认值为 7200
- [ ] 3.4 **[GREEN]** 设置 misfire_grace_time 默认值
- [ ] 3.5 **[RED]** 编写测试：验证配置对象不可变（frozen）
- [ ] 3.6 **[REFACTOR]** 确保所有字段使用 frozen=True

## 4. Scheduler Protocol（TDD）

- [ ] 4.1 **[RED]** 编写 `test_scheduler_protocol.py`：验证可以导入 Scheduler Protocol
- [ ] 4.2 **[GREEN]** 在 `app/foundation/application/scheduler.py` 中定义 Scheduler Protocol
- [ ] 4.3 **[RED]** 编写测试：验证 Protocol 包含 `add_job()`、`start()`、`shutdown()` 方法
- [ ] 4.4 **[GREEN]** 定义 Protocol 方法签名
- [ ] 4.5 **[RED]** 编写测试：验证 `get_scheduler()` 返回 Scheduler 类型
- [ ] 4.6 **[GREEN]** 在 `app/foundation/interfaces/scheduler.py` 中实现 `get_scheduler()` 函数

## 5. AsyncIOSchedulerImpl 实现（TDD）

- [ ] 5.1 **[RED]** 编写 `test_asyncio_scheduler_impl.py`：验证创建 `AsyncIOSchedulerImpl()` 实例
- [ ] 5.2 **[GREEN]** 创建 `app/foundation/infrastructure/scheduler.py` 并实现基础类
- [ ] 5.3 **[RED]** 编写测试：验证 `scheduler.add_job(config, task_callable)` 注册任务
- [ ] 5.4 **[GREEN]** 实现 add_job 方法（使用 APScheduler）
- [ ] 5.5 **[RED]** 编写测试：验证 `scheduler.start()` 启动调度器
- [ ] 5.6 **[GREEN]** 实现 start 方法
- [ ] 5.7 **[RED]** 编写测试：验证 `scheduler.shutdown(wait=True)` 关闭调度器
- [ ] 5.8 **[GREEN]** 实现 shutdown 方法
- [ ] 5.9 **[RED]** 编写 `test_wrapped_task_logging.py`：验证任务执行记录开始日志
- [ ] 5.10 **[GREEN]** 实现 wrapped_task 包装函数（记录开始日志）
- [ ] 5.11 **[RED]** 编写测试：验证任务成功时记录 duration_ms
- [ ] 5.12 **[GREEN]** 在 wrapped_task 中添加成功日志和耗时计算
- [ ] 5.13 **[RED]** 编写测试：验证任务失败时记录 error 日志和 exc_info
- [ ] 5.14 **[GREEN]** 在 wrapped_task 中添加异常处理和错误日志
- [ ] 5.15 **[REFACTOR]** 提取日志记录到独立函数，使用 structlog

## 6. ModuleRegistry 任务注册机制（TDD）

- [ ] 6.1 **[RED]** 编写 `test_module_registry.py`：验证创建 ModuleRegistry 实例
- [ ] 6.2 **[GREEN]** 在 `app/foundation/application/module_registry.py` 中实现 ModuleRegistry 类
- [ ] 6.3 **[RED]** 编写测试：验证实例状态隔离（r1 和 r2 的 `_scheduled_task_factories` 独立）
- [ ] 6.4 **[GREEN]** 使用实例变量而非类变量存储状态
- [ ] 6.5 **[RED]** 编写测试：验证 `register_scheduled_tasks(factory)` 添加任务工厂
- [ ] 6.6 **[GREEN]** 实现 register_scheduled_tasks 方法
- [ ] 6.7 **[RED]** 编写测试：验证 `register_all_to_scheduler(scheduler)` 调用所有工厂
- [ ] 6.8 **[GREEN]** 实现 register_all_to_scheduler 方法
- [ ] 6.9 **[RED]** 编写 `test_module_registry_validation.py`：验证 config.id 缺失时抛出 ValueError
- [ ] 6.10 **[GREEN]** 实现任务验证机制
- [ ] 6.11 **[REFACTOR]** 提取验证逻辑到 `_validate_tasks()` 方法
- [ ] 6.12 **[RED]** 编写架构测试：验证 foundation 不 import 业务模块
- [ ] 6.13 **[GREEN]** 在 `app/modules/__init__.py` 中添加 `register_scheduled_tasks()` 框架

## 7. Data Engineering 模块定时任务（TDD）

- [ ] 7.1 **[RED]** 编写 `test_scheduled_tasks_config.py`：验证 `get_scheduled_tasks()` 返回任务配置列表
- [ ] 7.2 **[GREEN]** 创建 `app/modules/data_engineering/interfaces/schedulers/tasks.py` 并实现 get_scheduled_tasks
- [ ] 7.3 **[RED]** 编写测试：验证任务 ID 为 `de.sync_stock_daily_increment`
- [ ] 7.4 **[GREEN]** 配置任务 ID 和 CronTrigger（hour=16, minute=30）
- [ ] 7.5 **[RED]** 编写测试：验证 `max_instances=1`、`coalesce=True`、`misfire_grace_time=7200`
- [ ] 7.6 **[GREEN]** 设置任务配置参数
- [ ] 7.7 **[RED]** 编写 `test_task_callables.py`：验证 `create_task_callables()` 返回 async callable 映射
- [ ] 7.8 **[GREEN]** 实现 create_task_callables 函数
- [ ] 7.9 **[RED]** 编写测试：验证 async callable 自行管理 Session 生命周期
- [ ] 7.10 **[GREEN]** 在 async callable 中实现 session 创建→Handler 构造→执行→关闭
- [ ] 7.11 **[RED]** 编写测试：验证任务失败时不自动重试，记录错误日志
- [ ] 7.12 **[GREEN]** 实现异常处理逻辑（记录日志并重新抛出）
- [ ] 7.13 **[REFACTOR]** 提取 session 管理到上下文管理器
- [ ] 7.14 **[RED]** 编写测试：验证 `create_scheduled_tasks()` 返回 (configs, task_callables) 元组
- [ ] 7.15 **[GREEN]** 在 `interfaces/schedulers/__init__.py` 中实现 create_scheduled_tasks
- [ ] 7.16 **[GREEN]** 在 `app/modules/__init__.py` 中注册 data_engineering 任务

## 8. 应用启动集成（TDD）

- [ ] 8.1 **[RED]** 编写 `test_lifespan_scheduler.py`：验证 lifespan 初始化调度器
- [ ] 8.2 **[GREEN]** 在 `app/interfaces/main.py` 的 lifespan 中创建调度器实例
- [ ] 8.3 **[RED]** 编写测试：验证 lifespan 创建 ModuleRegistry 并注册任务
- [ ] 8.4 **[GREEN]** 在 lifespan 中创建 ModuleRegistry 并调用注册
- [ ] 8.5 **[RED]** 编写测试：验证 lifespan 启动调度器
- [ ] 8.6 **[GREEN]** 在 lifespan 中调用 scheduler.start()
- [ ] 8.7 **[RED]** 编写测试：验证应用关闭时调度器正确 shutdown
- [ ] 8.8 **[GREEN]** 在 lifespan 的 yield 后调用 scheduler.shutdown()
- [ ] 8.9 **[REFACTOR]** 提取调度器初始化逻辑到独立函数

## 9. 集成测试与架构验证

- [ ] 9.1 **[RED]** 编写集成测试：验证完整任务执行流程（注册→调度→执行→日志）
- [ ] 9.2 **[GREEN]** 编写集成测试辅助函数和 fixture
- [ ] 9.3 **[RED]** 编写架构测试：验证 foundation 模块依赖约束
- [ ] 9.4 **[GREEN]** 在架构测试中添加 foundation 检查用例
- [ ] 9.5 **[RED]** 编写测试：验证 import-linter forbidden contract
- [ ] 9.6 **[GREEN]** 运行 import-linter 验证依赖约束

## 10. 验证与部署

- [ ] 10.1 运行 `make ci` 验证所有测试通过
- [ ] 10.2 运行 import-linter 验证依赖约束
- [ ] 10.3 更新 README 或部署文档，说明调度器配置
- [ ] 10.4 在代码审查中验证模块注册机制
- [ ] 10.5 部署到生产环境并监控日志输出
