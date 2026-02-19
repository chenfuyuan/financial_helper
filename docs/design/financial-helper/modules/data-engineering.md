# DATA_ENGINEERING（数据工程层）

**日期：** 2026-02-19
**作者：** financial_helper 团队

---

## 3.2 DATA_ENGINEERING（数据工程层）

**职责：** 负责所有金融数据的获取、清洗、转换和加载，提供标准化的数据接口。

**核心约束：**
1. **存储最完整的数据** - 其他模块按需获取数据，不重复存储
2. **调用 Foundation** - 使用 foundation 的 crawler、cache、notification 等服务

**子模块：**
- `data_source_manager` - 数据源管理器（Tushare、AkShare、Custom Crawler）
- `etl_pipeline` - ETL处理流程
- `data_quality` - 数据质量检测
- `data_warehouse` - 数据仓库

**暴露接口：**
- `DataSource.get_stock_info(code) -> StockInfo`
- `DataSource.get_kline(code, period) -> KlineData`
- `DataSource.get_financial_data(code) -> FinancialData`
- `ETL.extract_transform_load(raw_data) -> CleanData`
- `DataQuality.validate(data) -> QualityReport`
- `DataWarehouse.query(sql) -> ResultSet`

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
