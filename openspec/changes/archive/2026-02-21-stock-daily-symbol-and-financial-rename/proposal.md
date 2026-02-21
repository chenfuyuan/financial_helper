## Why

为了提升数据模型的标准化和一致性，需要在 stock_daily 表中新增 symbol 字段，并将 financial_indicator 表重命名为 stock_financial 同时新增 symbol 字段。这些变更将使数据结构更符合命名规范，提高代码的可读性和维护性。

## What Changes

- **BREAKING**: stock_daily 表新增 symbol 字段（位于 third_code 后面）
- **BREAKING**: financial_indicator 表重命名为 stock_financial
- **BREAKING**: stock_financial 表新增 symbol 字段（位于 third_code 后面）
- **BREAKING**: 相关文件名从 financial_indicator 重命名为 stock_financial
- 更新相关的实体类、映射器、仓储等代码以支持新的表名和字段

## Capabilities

### New Capabilities
- `stock-daily-symbol-add`: 为 stock_daily 实体和表新增 symbol 字段支持
- `stock-financial-rename`: 将 financial_indicator 重命名为 stock_financial 并新增 symbol 字段

### Modified Capabilities
- `stock-daily-sync`: 需要更新以支持新的 symbol 字段
- `finance-indicator-sync`: 需要更新以支持新的表名 stock_financial 和 symbol 字段

## Impact

- 数据库表结构变更（需要迁移脚本）
- 实体类字段变更
- 持久化映射器更新
- 仓储接口和实现更新
- 应用层服务更新
- API 接口可能需要更新
- 相关测试用例更新
- 文件重命名可能影响导入路径
