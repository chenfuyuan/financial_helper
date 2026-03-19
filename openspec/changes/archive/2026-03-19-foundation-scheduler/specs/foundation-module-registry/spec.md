## ADDED Requirements

### Requirement: 模块注册器提供任务工厂注册接口

系统 SHALL 提供 ModuleRegistry 类（使用实例方法而非类方法），允许业务模块通过 `register_scheduled_tasks()` 方法注册自己的任务工厂。

#### Scenario: 业务模块注册任务工厂
- **WHEN** 业务模块调用 `registry.register_scheduled_tasks(factory)`
- **THEN** 任务工厂被添加到该实例的 `_scheduled_task_factories` 列表中

### Requirement: ModuleRegistry 实例状态隔离

系统 SHALL 确保 ModuleRegistry 使用实例变量（`__init__` 中初始化）而非类变量存储任务工厂列表，保证不同实例之间状态隔离，避免测试污染。

#### Scenario: 实例状态隔离
- **WHEN** 创建两个 ModuleRegistry 实例 r1 和 r2，向 r1 注册任务
- **THEN** r2 的 `_scheduled_task_factories` 列表为空

### Requirement: 任务工厂返回配置和 async callable 映射

系统 SHALL 定义任务工厂函数签名（`ScheduledTaskFactory` TypeAlias），返回值为 `(configs, task_callables)` 元组，其中 configs 是任务配置列表，task_callables 是任务 ID 到 async callable 的映射。

#### Scenario: 创建任务工厂
- **WHEN** 业务模块实现任务工厂函数
- **THEN** 工厂函数返回 `(list[ScheduledTaskConfig], dict[str, Callable[[], Awaitable[None]]])`，dict 中的值是可直接 await 的 async callable

### Requirement: 模块注册器统一注册所有任务到调度器

系统 SHALL 提供 `register_all_to_scheduler(scheduler)` 实例方法，遍历所有注册的任务工厂，将任务配置和 async callable 传递给调度器。

#### Scenario: 注册所有模块的任务
- **WHEN** 应用启动时调用 `registry.register_all_to_scheduler(scheduler)`
- **THEN** 遍历所有任务工厂，为每个任务配置调用 `scheduler.add_job(config, task_callable)`

### Requirement: 任务工厂通过闭包捕获依赖

系统 SHALL 支持任务工厂通过闭包捕获 `session_factory` 等依赖，任务执行函数自行管理 Session 生命周期，不通过 Mediator 分发。

#### Scenario: 任务工厂使用 session_factory
- **WHEN** 创建任务工厂时通过闭包捕获 `session_factory`
- **THEN** 任务 async callable 内部自行创建 session → 构造 Handler → 执行 → 关闭 session

### Requirement: 任务验证机制

系统 SHALL 验证每个任务配置都有对应的 async callable，若缺失则抛出 ValueError，错误信息包含任务 ID 和模块名。

#### Scenario: 验证任务完整性
- **WHEN** 注册任务时 config.id 不在 task_callables 中
- **THEN** 抛出 `ValueError`，包含任务 ID 和模块名信息

### Requirement: foundation 不依赖业务模块

系统 SHALL 确保 foundation 模块不主动 import 任何业务模块，所有依赖通过 ModuleRegistry 的注册机制注入。通过 import-linter forbidden contract 自动检查。

#### Scenario: foundation 模块的依赖检查
- **WHEN** 检查 foundation 模块的 import 语句
- **THEN** 不应出现 `from app.modules.*` 的导入

### Requirement: 业务模块主动注册

系统 SHALL 要求业务模块在 `app/modules/__init__.py` 的 `register_scheduled_tasks()` 函数中主动注册定时任务。Router 注册仍由 `app/interfaces/module_registry.py` 负责，职责分离。

#### Scenario: 业务模块注册流程
- **WHEN** 新增业务模块时
- **THEN** 需要在 `app/modules/__init__.py` 的 `register_scheduled_tasks()` 中添加该模块的任务注册代码
