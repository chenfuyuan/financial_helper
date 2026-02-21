# Spec: Stock Financial 重命名和 Symbol 字段添加 (stock-financial-rename)

将 financial_indicator 表重命名为 stock_financial 并新增 symbol 字段，提升数据命名规范和标准化程度。

## Purpose

通过表重命名和字段添加，使财务指标数据结构更符合命名规范，同时提供更标准的股票标识符。

## ADDED Requirements

### Requirement: StockFinancial 实体新增 symbol 字段

StockFinancial 领域实体 SHALL 新增 symbol 字段，用于存储股票的标准代码标识符。

#### Scenario: 创建包含 symbol 的 StockFinancial 实体
- **WHEN** 系统创建 StockFinancial 实体时
- **THEN** 该实体包含 symbol 字段，且该字段位于 third_code 字段之后

#### Scenario: symbol 字段可为空
- **WHEN** 创建或更新 StockFinancial 实体时未提供 symbol 值
- **THEN** symbol 字段允许为 NULL，不抛出异常

### Requirement: StockFinancial 持久化支持 symbol 字段

StockFinancialPersistenceMapper SHALL 支持将实体的 symbol 字段映射到数据库表的对应字段。

#### Scenario: 映射器包含 symbol 字段
- **WHEN** 调用 StockFinancialPersistenceMapper 的 to_row 方法时
- **THEN** 返回的字典包含 symbol 键，其值为实体的 symbol 字段值

#### Scenario: 数据库表包含 symbol 列
- **WHEN** 数据库迁移完成后
- **THEN** stock_financial 表包含 symbol 列，数据类型为 VARCHAR，位于 third_code 列之后

### Requirement: 数据库迁移重命名表并添加字段

系统 SHALL 提供 Alembic 迁移脚本将 financial_indicator 表重命名为 stock_financial 并添加 symbol 字段。

#### Scenario: 执行表重命名迁移
- **WHEN** 运行 Alembic 升级命令时
- **THEN** financial_indicator 表被重命名为 stock_financial，同时添加 symbol 列

#### Scenario: 迁移脚本可回滚
- **WHEN** 运行 Alembic 降级命令时
- **THEN** stock_financial 表被重命名回 financial_indicator，symbol 列被移除

### Requirement: 文件重命名和代码更新

所有与 financial_indicator 相关的代码文件 SHALL 被重命名为 stock_financial，并更新所有引用。

#### Scenario: 实体类文件重命名
- **WHEN** 迁移完成后
- **THEN** financial_indicator.py 被重命名为 stock_financial.py，类名更新为 StockFinancial

#### Scenario: 映射器文件重命名
- **WHEN** 迁移完成后
- **THEN** financial_indicator_persistence_mapper.py 被重命名为 stock_financial_persistence_mapper.py

#### Scenario: 仓储文件重命名
- **WHEN** 迁移完成后
- **THEN** financial_indicator_repository.py 被重命名为 stock_financial_repository.py

#### Scenario: 所有导入语句更新
- **WHEN** 文件重命名完成后
- **THEN** 所有代码中的导入语句都更新为新的文件路径和类名
