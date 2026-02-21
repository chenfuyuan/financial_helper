# Spec: Stock Daily Symbol 字段添加 (stock-daily-symbol-add)

为 stock_daily 表和实体新增 symbol 字段支持，提升数据标准化程度。

## Purpose

在现有的 stock_daily 数据结构基础上新增 symbol 字段，为股票数据提供更标准的标识符。

## ADDED Requirements

### Requirement: StockDaily 实体新增 symbol 字段

StockDaily 领域实体 SHALL 新增 symbol 字段，用于存储股票的标准代码标识符。

#### Scenario: 创建包含 symbol 的 StockDaily 实体
- **WHEN** 系统创建 StockDaily 实体时
- **THEN** 该实体包含 symbol 字段，且该字段位于 third_code 字段之后

#### Scenario: symbol 字段可为空
- **WHEN** 创建或更新 StockDaily 实体时未提供 symbol 值
- **THEN** symbol 字段允许为 NULL，不抛出异常

### Requirement: StockDaily 持久化支持 symbol 字段

StockDailyPersistenceMapper SHALL 支持将实体的 symbol 字段映射到数据库表的对应字段。

#### Scenario: 映射器包含 symbol 字段
- **WHEN** 调用 StockDailyPersistenceMapper 的 to_row 方法时
- **THEN** 返回的字典包含 symbol 键，其值为实体的 symbol 字段值

#### Scenario: 数据库表包含 symbol 列
- **WHEN** 数据库迁移完成后
- **THEN** stock_daily 表包含 symbol 列，数据类型为 VARCHAR，位于 third_code 列之后

### Requirement: StockDaily 同步支持 symbol 字段

股票日线数据同步流程 SHALL 支持获取和存储 symbol 字段数据。

#### Scenario: 同步获取 symbol 数据
- **WHEN** 从外部数据源同步股票日线数据时
- **THEN** 系统尝试获取 symbol 信息并填充到 StockDaily 实体的 symbol 字段

#### Scenario: symbol 数据缺失处理
- **WHEN** 外部数据源未提供 symbol 信息时
- **THEN** 系统将 symbol 字段设置为 NULL，继续处理其他字段

### Requirement: 数据库迁移添加 symbol 字段

系统 SHALL 提供 Alembic 迁移脚本为 stock_daily 表添加 symbol 字段。

#### Scenario: 执行迁移脚本
- **WHEN** 运行 Alembic 升级命令时
- **THEN** stock_daily 表成功添加 symbol 列，位置在 third_code 列之后

#### Scenario: 迁移脚本可回滚
- **WHEN** 运行 Alembic 降级命令时
- **THEN** symbol 列被安全移除，表结构恢复到迁移前状态
