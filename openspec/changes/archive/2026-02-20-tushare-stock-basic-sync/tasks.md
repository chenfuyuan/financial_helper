## 1. 模块骨架与领域层

- [x] 1.1 在 pyproject.toml 的 importlinter containers 中追加 app.modules.data_engineering
- [x] 1.2 创建 data_engineering 各层目录及 __init__.py（domain、application/commands、infrastructure/models、interfaces/api）
- [x] 1.3 实现 domain/stock_basic.py：StockStatus 与 DataSource 枚举、StockBasic 实体（含 id、created_at、updated_at、version 及业务字段）
- [x] 1.4 实现 domain/stock_gateway.py：StockGateway 接口，fetch_stock_basic() -> list[StockBasic]
- [x] 1.5 实现 domain/stock_basic_repository.py：StockBasicRepository 接口，upsert_many(stocks) -> None
- [x] 1.6 编写 domain 单元测试 test_stock_basic.py，验证实体与枚举，运行 make architecture-check 与 pytest 通过

## 2. 基础设施：模型与迁移

- [x] 2.1 实现 infrastructure/models/stock_basic_model.py：表 stock_basic，含基础字段（id、created_at、updated_at、version）与业务字段，UNIQUE(source, third_code)
- [x] 2.2 新增 Alembic 迁移创建 stock_basic 表，downgrade 删除该表
- [x] 2.3 本地执行 make migrate 验证迁移成功

## 3. 基础设施：仓储与网关实现

- [x] 3.1 实现 SqlAlchemyStockBasicRepository：upsert_many 使用 ON CONFLICT (source, third_code) DO UPDATE，维护 created_at 不变、updated_at 与 version 递增
- [x] 3.2 编写仓储集成测试：首次插入、再次更新同 (source, third_code)、幂等性断言
- [x] 3.3 定义领域异常（如 ExternalStockServiceError）供网关解析失败时抛出
- [x] 3.4 实现 TuShareStockGateway：调用 TuShare stock_basic，逐条解析为 StockBasic，任一条解析失败即抛异常
- [x] 3.5 编写 TuShareStockGateway 单测：字段映射（ts_code→third_code、list_status→StockStatus）、list_date 解析、解析失败则整批抛错

## 4. 应用层：命令与 Handler

- [x] 4.1 实现 application/commands/sync_stock_basic.py：SyncStockBasic 命令（实现 Command）
- [x] 4.2 实现 SyncStockBasicHandler：依赖 StockGateway、StockBasicRepository，handle 内 fetch_stock_basic → upsert_many，返回 synced_count
- [x] 4.3 编写 Handler 单测：fake 网关与仓储，验证 upsert_many 被正确调用；网关抛错时 handle 向上抛、不提交

## 5. 接口层与集成

- [x] 5.1 实现 interfaces/api/stock_basic_router.py：POST /sync，Depends(get_uow)，构造 Gateway、Repository、Handler，handle 后 uow.commit()，成功返回 synced_count（及可选 duration_ms）
- [x] 5.2 在 main.py 中 include_router，路径为 /data-engineering/stock-basic（或与 spec 一致的 prefix）
- [x] 5.3 编写 API 测试：POST 同步接口成功返回 2xx 与 synced_count；网关异常时返回 5xx 或统一错误格式

## 6. 依赖与收尾

- [x] 6.1 在 pyproject.toml 或配置中增加 TuShare 依赖及 TUSHARE_TOKEN（或等效）配置
- [x] 6.2 运行 make ci 全量通过，必要时补充文档或 changelog（若 lint-imports 报 Missing layer，可保留 router/handler 中对 application、infrastructure、domain 的包级 import）
