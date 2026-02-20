## Why

当前系统已实现股票基础信息同步，但缺少股票日线行情数据的同步功能。日线行情是 A 股投资分析的核心数据，用于技术分析、回测、趋势判断等场景。实现该功能可以为 MARKET_INSIGHT、RESEARCH、COORDINATOR 等模块提供关键的数据支撑。

## What Changes

- 新增股票日线行情数据实体（StockDaily）
- 新增股票日线行情网关接口与 TuShare 实现
- 新增股票日线行情仓储接口与 SQLAlchemy 实现
- 新增同步股票日线行情的 Application Command 与 Handler
- 新增 HTTP 接口触发日线行情同步
- 支持按日期范围同步股票日线行情
- 支持按股票代码列表同步日线行情

## Capabilities

### New Capabilities
- `stock-daily-sync`: 股票日线行情数据同步功能，支持从 TuShare 获取日线行情数据并持久化到本地数据库，提供 HTTP 触发接口

### Modified Capabilities
- 无

## Impact

- 新增代码位于 `src/app/modules/data_engineering/` 下
- 新增数据库表 `stock_daily`
- 新增 HTTP 端点 `POST /data-engineering/stock-daily/sync`
- 依赖 FOUNDATION 层的 crawler、cache、notification 服务
- 为 KNOWLEDGE_CENTER、MARKET_INSIGHT、RESEARCH、COORDINATOR 模块提供日线数据支持
