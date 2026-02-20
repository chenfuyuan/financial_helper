# Tushare 股票财务指标同步 Tasks

> 详细实现步骤见 `plan.md`。每完成一步请打勾并 commit。

---

## Task 1: 领域实体与接口定义

- [x] 1.1 运行测试确认失败（`test_financial_indicator.py` ImportError）
- [x] 1.2 创建 `domain/entities/financial_indicator.py`（`FinancialIndicator` dataclass，~100 个字段）
- [x] 1.3 创建 `domain/gateways/financial_indicator_gateway.py`（`FinancialIndicatorGateway` ABC）
- [x] 1.4 创建 `domain/repositories/financial_indicator_repository.py`（`FinancialIndicatorRepository` ABC）
- [x] 1.5 创建 `tests/unit/.../test_financial_indicator.py`（5 个单元测试）
- [x] 1.6 运行测试确认全部通过
- [x] 1.7 `git commit -m "feat(data_engineering): add FinancialIndicator entity and domain interfaces"`

---

## Task 2: SQLAlchemy 模型与数据库迁移

- [x] 2.1 创建 `infrastructure/models/financial_indicator_model.py`（`FinancialIndicatorModel`，唯一约束 `uq_financial_indicator_key`）
- [x] 2.2 在 `migrations/env.py` 中 import `FinancialIndicatorModel`
- [x] 2.3 运行 `alembic revision --autogenerate -m "add financial indicator table"`
- [x] 2.4 检查生成的迁移文件（表结构、唯一约束、字段类型正确）
- [x] 2.5 运行 `alembic upgrade head` 确认迁移成功
- [x] 2.6 `git commit -m "feat(data_engineering): add financial_indicator SQLAlchemy model and migration"`

---

## Task 3: Repository 实现（TDD）

- [x] 3.1 创建 `tests/integration/.../test_sqlalchemy_financial_indicator_repository.py`（3 个集成测试）
- [x] 3.2 运行测试确认失败（ImportError）
- [x] 3.3 创建 `infrastructure/repositories/mappers/financial_indicator_persistence_mapper.py`
- [x] 3.4 创建 `infrastructure/repositories/sqlalchemy_financial_indicator_repository.py`（`upsert_many` + `get_latest_end_date`，BATCH_SIZE=50）
- [x] 3.5 运行集成测试确认全部通过
- [x] 3.6 `git commit -m "feat(data_engineering): add FinancialIndicator repository with upsert"`

---

## Task 4: Tushare Gateway + Mapper（TDD）

- [x] 4.1 创建 `tests/unit/.../test_tushare_finance_indicator_gateway.py`（3 个单元测试）
- [x] 4.2 运行测试确认失败（ImportError）
- [x] 4.3 创建 `infrastructure/gateways/mappers/tushare_finance_indicator_mapper.py`（使用 `dataclasses.fields` 遍历字段）
- [x] 4.4 创建 `infrastructure/gateways/tushare_finance_indicator_gateway.py`（TokenBucket + 检测式分页，PAGE_SIZE=100）
- [x] 4.5 运行单元测试确认全部通过
- [x] 4.6 `git commit -m "feat(data_engineering): add TuShare finance indicator gateway with pagination"`

---

## Task 5: Commands + Handlers（TDD）

- [x] 5.1 创建 `application/commands/sync_finance_indicator_commands.py`（3 个 Command dataclass + `SyncFinanceIndicatorResult`）
- [x] 5.2 创建 `tests/unit/.../test_sync_finance_indicator_handlers.py`（3 个单元测试）
- [x] 5.3 运行测试确认失败（ImportError）
- [x] 5.4 创建 `sync_finance_indicator_full_handler.py`（全量：无 start_date，逐股独立事务）
- [x] 5.5 创建 `sync_finance_indicator_by_stock_handler.py`（单股：单次事务）
- [x] 5.6 创建 `sync_finance_indicator_increment_handler.py`（增量：`get_latest_end_date` → `start_date = latest + 1day`）
- [x] 5.7 运行单元测试确认全部通过
- [x] 5.8 `git commit -m "feat(data_engineering): add finance indicator sync handlers"`

---

## Task 6: HTTP Router + 依赖注入 + API 集成测试

- [x] 6.1 创建 `tests/api/.../test_finance_indicator_router.py`（3 个 API 集成测试，mock handlers）
- [x] 6.2 运行测试确认失败（404 / ImportError）
- [x] 6.3 创建 `interfaces/api/finance_indicator_router.py`（3 个端点：`/sync/full`、`/sync/by-stock/{ts_code}`、`/sync/increment`）
- [x] 6.4 更新 `interfaces/dependencies.py`（追加 3 个 `get_sync_finance_indicator_*_handler` 函数）
- [x] 6.5 在 `module_registry.py` 注册 `finance_indicator_router`（prefix `/api/v1`）
- [x] 6.6 运行 API 集成测试确认全部通过
- [x] 6.7 运行全量回归 `pytest tests/ -v --tb=short`
- [x] 6.8 `git commit -m "feat(data_engineering): add finance indicator HTTP router and DI wiring"`

---

## 完成验证

- [x] `pytest tests/ -v --tb=short` 全部通过（4 个预存在失败与本次无关）
- [x] `pytest tests/architecture/` 架构守护通过
- [x] `alembic current` 迁移状态正常
