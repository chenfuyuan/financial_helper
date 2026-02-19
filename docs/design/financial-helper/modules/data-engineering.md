# DATA_ENGINEERING（数据工程层）

**日期：** 2026-02-19
**作者：** financial_helper 团队

---

## 3.2 DATA_ENGINEERING（数据工程层）

**职责：** 负责所有金融数据的获取、清洗、转换和加载，提供标准化的数据接口。

**核心约束：**
1. **存储最完整的数据** - 其他模块按需获取数据，不重复存储
2. **调用 Foundation** - 使用 foundation 的 crawler、cache、notification 等服务

### 模块内分层（复利工程约定）

本模块作为 **domain / infrastructure 子目录 + mappers 内聚** 的参考实现：

| 层 | 子目录 | 说明 |
|----|--------|------|
| **domain** | **entities/** | 实体、值对象、枚举（如 `StockBasic`, `StockStatus`, `DataSource`） |
| **domain** | **gateways/** | 外部数据源网关**接口**（如 `StockGateway.fetch_stock_basic()`） |
| **domain** | **repositories/** | 仓储**接口**（如 `StockBasicRepository.upsert_many()`） |
| **infrastructure** | **gateways/** | 外部适配实现（如 TuShare）；其 **mappers/** 负责「API 响应 → 领域模型」 |
| **infrastructure** | **repositories/** | 持久化仓储实现（如 SQLAlchemy）；其 **mappers/** 负责「领域模型 → 持久化行」 |
| **infrastructure** | **models/** | SQLAlchemy 表模型（如 `StockBasicModel`） |

**已实现示例：** 股票基础信息同步（StockBasic）
- Domain：`entities/stock_basic.py`、`gateways/stock_gateway.py`、`repositories/stock_basic_repository.py`
- Infra：`gateways/tushare_stock_gateway.py` + `gateways/mappers/tushare_stock_basic_mapper.py`；`repositories/sqlalchemy_stock_basic_repository.py` + `repositories/mappers/stock_basic_persistence_mapper.py`；`models/stock_basic_model.py`

**规划子模块（待实现）：**
- `data_source_manager` - 数据源管理器（Tushare、AkShare、Custom Crawler）
- `etl_pipeline` - ETL 处理流程
- `data_quality` - 数据质量检测
- `data_warehouse` - 数据仓库

**暴露接口（当前/规划）：**
- 当前：`StockGateway.fetch_stock_basic() -> list[StockBasic]`；`StockBasicRepository.upsert_many(stocks)`；HTTP `POST /data-engineering/stock-basic/sync`
- 规划：`DataSource.get_stock_info(code)`、`DataSource.get_kline(code, period)`、`ETL.extract_transform_load(raw_data)`、`DataQuality.validate(data)`、`DataWarehouse.query(sql)` 等

**依赖：**
- ↳ FOUNDATION (task_scheduler, crawler, notification, cache)

**被依赖：**
- ◀ KNOWLEDGE_CENTER (需要数据构建知识图谱)
- ◀ MARKET_INSIGHT (需要市场数据进行分析)
- ◀ RESEARCH (需要数据用于研究分析)
- ◀ COORDINATOR (需要数据用于分析流程)

**禁止：**
- ✗ 直接调用 LLM 服务（应通过 llm_gateway）
- ✗ 直接访问图数据库（应通过 knowledge_center）
- ✗ 包含分析逻辑（只负责数据供给，不做分析）
