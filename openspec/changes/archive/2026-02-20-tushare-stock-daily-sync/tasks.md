# Tasks: 股票日线行情数据同步

基于 plan.md 的 TDD 实施计划。

- [x] Task 1: 创建数据库模型与领域实体
  - [x] 编写 `StockDaily` 和 `StockDailySyncFailure` 实体
  - [x] 编写 `StockDailyModel` 和 `StockDailySyncFailureModel`
  - [x] 在 `migrations/env.py` 中注册模型并生成迁移脚本


- [x] Task 2: 定义接口抽象
  - [x] 定义 `StockDailyGateway` 接口
  - [x] 定义 `StockDailyRepository` 接口
  - [x] 定义 `StockDailySyncFailureRepository` 接口


- [x] Task 3: 实现 StockDaily 仓储 (TDD)
  - [x] 编写 Repository 集成测试 (`test_stock_daily_repository.py`)
  - [x] 运行测试确认失败
  - [x] 实现 `StockDailyPersistenceMapper` 和 `SqlAlchemyStockDailyRepository`
  - [x] 运行测试确认通过
  - [x] 提交代码


- [x] Task 4: 实现 Handler (历史同步)
  - [x] 编写 `SyncStockDailyHistory` Command 和对应的 Handler
  - [x] 提交代码


- [x] Task 5: 剩余组件实现（按需展开）
  - [x] TuShare 网关与 Mapper 实现（含 Token Bucket）
  - [x] 增量同步与失败重试 Handler 实现
  - [x] HTTP Router 注册与依赖注入
  - [x] 编写相关测试并提交
