# AKShare 概念板块同步 — 任务清单

> 详细实现步骤见 `plan-part1.md`、`plan-part2a.md`、`plan-part2b.md`
> TDD 规则：每个任务先写失败测试 → 确认失败 → 写最小实现 → 确认通过 → commit

---

## 进度追踪

| 状态 | 含义 |
|------|------|
| `[ ]` | 未开始 |
| `[~]` | 进行中 |
| `[x]` | 完成 |

---

## Task 0 — 依赖 + DataSource 枚举扩展
> 📄 `plan-part1.md` § Task 0

- [x] 0.1 `pyproject.toml` 追加 `akshare>=1.12.0`
- [x] 0.2 `DataSource` 枚举追加 `AKSHARE = "AKSHARE"`
- [x] 0.3 `pip install akshare` + 验证导入
- [x] 0.4 commit: `feat(data_engineering): add akshare dependency and AKSHARE DataSource`

---

## Task 1 — 领域实体 Concept + ConceptStock（含哈希方法）
> 📄 `plan-part1.md` § Task 1 | 测试: `tests/unit/modules/data_engineering/domain/test_concept_hash.py`

- [x] 1.1 写失败测试（5 个 hash 断言）
- [x] 1.2 运行确认失败 `pytest tests/unit/.../test_concept_hash.py -v`
- [x] 1.3 创建 `src/app/modules/data_engineering/domain/entities/concept.py`
- [x] 1.4 创建 `src/app/modules/data_engineering/domain/entities/concept_stock.py`
- [x] 1.5 运行确认 5 tests PASSED
- [x] 1.6 commit: `feat(data_engineering): add Concept/ConceptStock entities with hash computation`

---

## Task 2 — 领域接口：异常、ConceptGateway、仓储接口
> 📄 `plan-part1.md` § Task 2

- [x] 2.1 扩展 `src/app/modules/data_engineering/domain/exceptions.py`（添加 `ExternalConceptServiceError`、`ConceptNotFoundError`）
- [x] 2.2 创建 `src/app/modules/data_engineering/domain/gateways/concept_gateway.py`
- [x] 2.3 创建 `src/app/modules/data_engineering/domain/repositories/concept_repository.py`
- [x] 2.4 创建 `src/app/modules/data_engineering/domain/repositories/concept_stock_repository.py`
- [x] 2.5 验证 `python -c "from ... import ..."`
- [x] 2.6 commit: `feat(data_engineering): add concept domain interfaces (gateway, repos, exceptions)`

---

## Task 3 — 基础设施：ORM 模型
> 📄 `plan-part1.md` § Task 3

- [x] 3.1 创建 `src/app/modules/data_engineering/infrastructure/models/concept_model.py`
- [x] 3.2 创建 `src/app/modules/data_engineering/infrastructure/models/concept_stock_model.py`
- [x] 3.3 在 `infrastructure/models/__init__.py` 追加两个 import
- [x] 3.4 验证模型可导入
- [x] 3.5 commit: `feat(data_engineering): add ConceptModel and ConceptStockModel ORM models`

---

## Task 4 — Alembic 迁移
> 📄 `plan-part1.md` § Task 4

- [x] 4.1 `alembic revision --autogenerate -m "add_concept_tables"`
- [x] 4.2 核查生成文件（外键级联删除、字段顺序）
- [x] 4.3 `alembic upgrade head`

---

## Task 5 — AkShareConceptMapper（单元测试）
> 📄 `plan-part1.md` § Task 5 | 测试: `tests/unit/.../gateways/mappers/test_akshare_concept_mapper.py`

- [x] 5.1 写失败测试（6 个 mapper 断言）
- [x] 5.2 运行确认 `ImportError`
- [x] 5.3 创建 `src/app/.../infrastructure/gateways/mappers/akshare_concept_mapper.py`
- [x] 5.4 运行确认 6 tests PASSED

---

## Task 6 — AkShareConceptGateway（单元测试）
> 📄 `plan-part2a.md` § Task 6 | 测试: `tests/unit/.../gateways/test_akshare_concept_gateway.py`

- [x] 6.1 写失败测试（4 个断言：成功路径 + 异常包装）
- [x] 6.2 运行确认 `ImportError`
- [x] 6.3 创建 `src/app/.../infrastructure/gateways/akshare_concept_gateway.py`
- [x] 6.4 运行确认 4 tests PASSED

---

## Task 7 — SqlAlchemyConceptRepository（集成测试）
> 📄 `plan-part2a.md` § Task 7 | 测试: `tests/integration/.../test_sqlalchemy_concept_repository.py`

- [x] 7.1 写失败测试（5 个断言：save/find/delete/update）
- [x] 7.2 运行确认 `ImportError`
- [x] 7.3 创建 `src/app/.../infrastructure/repositories/sqlalchemy_concept_repository.py`
- [x] 7.4 运行确认 5 tests PASSED

---

## Task 8 — SqlAlchemyConceptStockRepository（集成测试）
> 📄 `plan-part2a.md` § Task 8 | 测试: `tests/integration/.../test_sqlalchemy_concept_stock_repository.py`

- [x] 8.1 写失败测试（3 个断言：save_many/find/delete）
- [x] 8.2 运行确认 `ImportError`
- [x] 8.3 创建 `src/app/.../infrastructure/repositories/sqlalchemy_concept_stock_repository.py`
- [x] 8.4 运行确认 3 tests PASSED


---

## Task 9 — SyncConceptsHandler（单元测试）
> 📄 `plan-part2b.md` § Task 9 | 测试: `tests/unit/.../application/commands/test_sync_concepts_handler.py`

- [x] 9.1 写失败测试（5 个场景：新增/未变更/删除/异常/修改触发股票同步）
- [x] 9.2 运行确认 `ImportError`
- [x] 9.3 创建 `src/app/.../application/commands/sync_concepts.py`
- [x] 9.4 创建 `src/app/.../application/commands/sync_concepts_handler.py`（两级哈希同步算法）
- [x] 9.5 运行确认 5 tests PASSED

---

## Task 10 — GetConceptsHandler + GetConceptStocksHandler（单元测试）
> 📄 `plan-part2b.md` § Task 10 | 测试: `tests/unit/.../application/queries/test_concept_query_handlers.py`

- [x] 10.1 写失败测试（4 个场景：列表查询/空列表/成分股查询/404）
- [x] 10.2 运行确认 `ImportError`
- [x] 10.3 创建 `get_concepts.py` + `get_concepts_handler.py`
- [x] 10.4 创建 `get_concept_stocks.py` + `get_concept_stocks_handler.py`
- [x] 10.5 运行确认 4 tests PASSED

---

## Task 11 — 接口层：Router + Dependencies + 模块注册 + API 测试
> 📄 `plan-part2b.md` § Task 11 | 测试: `tests/api/modules/data_engineering/test_concept_router.py`

- [x] 11.1 写失败测试（3 个场景：sync/get list/404）
- [x] 11.2 运行确认路由 404
- [x] 11.3 创建 `src/app/.../interfaces/api/concept_router.py`（含 Pydantic Response Models）
- [x] 11.4 在 `interfaces/dependencies.py` 追加三个 factory 函数
- [x] 11.5 在 `interfaces/module_registry.py` 注册 `concept_router`
- [x] 11.6 在 `tests/api/conftest.py` 追加 concept 模型 import
- [x] 11.7 运行 API 测试确认通过
- [x] 11.8 `pytest tests/ -v --tb=short`（全量回归，无退步）
- [x] 11.9 `pytest tests/architecture/ -v`（架构守卫通过）

---

## 完成检查

```bash
# 全量测试
pytest tests/ -v --tb=short

# 架构守卫
pytest tests/architecture/ -v

# 覆盖率
pytest --cov=app --cov-report=term-missing
```

**预期新增测试数：** 5 + 6 + 5 + 3 + 5 + 4 + 3 = **31 个**
