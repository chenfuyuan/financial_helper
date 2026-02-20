
## Why

金融助手系统需要获取 A 股市场的概念板块及成分股关联关系数据，用于后续的市场分析、知识图谱构建和投资决策支持。目前系统仅有 TuShare 数据源，缺少概念板块相关数据，需要通过 AKShare 东方财富接口补充这一能力。

## What Changes

- 新增 AKShare 依赖
- 新增概念板块（Concept）领域实体和数据模型
- 新增概念-股票关联（ConceptStock）领域实体和数据模型
- 新增 ConceptGateway 网关接口及 AkShareConceptGateway 实现
- 新增 ConceptRepository 和 ConceptStockRepository 仓储接口及实现
- 新增概念板块同步 Command + Handler（基于哈希的精细增量同步）
- 新增概念板块相关 HTTP API 端点
- 扩展 DataSource 枚举，新增 AKSHARE 选项

## Capabilities

### New Capabilities
- `concept-sync`: 从 AKShare 东方财富数据源获取概念板块及成分股关联关系，支持基于哈希的精细增量同步
- `concept-query`: 查询概念板块列表及指定概念的成分股

### Modified Capabilities

## Impact

- 受影响代码：`src/app/modules/data_engineering/` 下的 domain、application、infrastructure、interfaces 层
- 新增 API：`/api/v1/data-engineering/concepts/*`
- 新增依赖：`akshare&gt;=1.12.0`
- 新增数据库表：`concept`、`concept_stock`

