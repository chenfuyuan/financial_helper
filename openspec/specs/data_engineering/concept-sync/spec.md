# Spec: 题材板块同步 (concept-sync)

从 AKShare 数据源全量同步题材板块信息及其成分股关系，采用批量操作和独立事务管理，确保数据一致性和性能优化。

## Requirements

### Requirement: 题材板块全量同步与批量操作

系统 SHALL 从 AKShare 全量同步所有题材板块及其成分股关系，采用批量 upsert 操作，避免逐条删除再插入的模式。

#### Scenario: 全量同步数据准备

- **WHEN** 用户通过 `POST /api/v1/data-engineering/concepts/sync` 触发题材同步
- **THEN** 系统从 AKShare 一次性获取所有题材板块数据
- **AND** 系统获取本地所有 source=AKSHARE 的题材数据
- **AND** 系统使用 `third_code` 作为键构建远程和本地数据的内存映射表
- **AND** 系统从 StockBasic 获取所有已上市股票用于代码匹配

#### Scenario: 批量 upsert 题材板块

- **WHEN** 系统已完成远程和本地题材映射表的准备
- **THEN** 系统创建待 upsert 的题材列表（所有远程题材）
- **AND** 对每个远程题材，系统计算内容哈希并设置 `last_synced_at`
- **AND** 系统使用 `concept_repo.save_many()` 执行批量 upsert 操作
- **AND** 系统记录处理的题材总数

#### Scenario: 批量同步题材成分股

- **WHEN** 所有题材完成批量 upsert
- **THEN** 对每个题材，系统从 AKShare 获取其成分股数据
- **AND** 系统使用 symbol 和 third_code 映射表匹配股票
- **AND** 系统构建包含正确 concept_id 引用的 ConceptStock 实体列表
- **AND** 系统使用 `concept_stock_repo.save_many()` 执行批量 upsert 操作
- **AND** 系统记录处理的股票关系总数

#### Scenario: 清理过时数据

- **WHEN** 所有题材完成独立处理后
- **THEN** 系统识别本地存在但远程数据中不存在的题材
- **AND** 对每个过时题材，系统在独立事务中删除其 ConceptStock 关系
- **AND** 系统在同一事务中删除过时的 Concept 实体
- **AND** 每个过时题材使用独立事务处理

#### Scenario: 事务管理

- **WHEN** 执行全量同步过程
- **THEN** 系统对每个题材的处理使用独立事务
- **AND** 每个事务包含题材 upsert 及其股票关系
- **AND** 每个事务在题材及其股票处理完成后提交
- **AND** 如果某个题材的事务失败，仅回滚该题材
- **AND** 系统继续独立处理其他题材
- **AND** 系统返回包含失败计数的详细同步结果

#### Scenario: 性能优化

- **WHEN** 处理大量题材数据
- **THEN** 系统使用批量操作最小化数据库交互次数
- **AND** 系统以可配置的批次大小处理题材
- **AND** 系统在关键里程碑记录进度日志
- **AND** 系统在处理过程中监控内存使用情况

### Requirement: 股票与 StockBasic 实体关联

- **WHEN** 保存题材成分股时
- **THEN** 系统从股票代码前缀推断交易所后缀（6→.SH, 0/3→.SZ, 4/8→.BJ）构建 `candidate_symbol`
- **AND** 系统首先尝试将 `candidate_symbol` 与预加载的 `StockBasic.symbol` 映射表匹配
- **AND** 如果匹配失败，系统尝试与预加载的 `StockBasic.third_code` 映射表匹配（source=TUSHARE）
- **AND** 如果两次匹配都失败，系统保存关系时将 `stock_symbol` 设为 NULL 并记录警告日志

### Requirement: 优雅处理 AKShare API 故障

- **WHEN** 同步过程中 AKShare API 调用失败（网络错误、解析错误、空响应）
- **THEN** 系统抛出 `ExternalConceptServiceError`
- **AND** 系统记录错误日志并在可能的情况下继续处理其他题材
- **AND** 系统向调用方传播包含适当上下文的错误

### Requirement: 处理 AKShare 空响应

- **WHEN** AKShare 返回空题材列表
- **THEN** 系统将其视为有效响应（非错误）
- **AND** 系统将所有本地 source=AKSHARE 的题材标记为已删除
- **AND** 同步结果反映删除计数

### Requirement: 内容哈希计算用于变更检测

系统 SHALL 为 Concept 和 ConceptStock 实体计算内容哈希，使用 SHA-256（截取前16位十六进制字符），以便在同步过程中进行高效的变更检测。

#### Scenario: 计算 Concept 内容哈希

- **WHEN** 准备同步的 Concept 实体时
- **THEN** 系统计算 `sha256(f"{source}|{third_code}|{name}")[:16]`
- **AND** 将哈希存储在 `content_hash` 字段中

#### Scenario: 计算 ConceptStock 内容哈希

- **WHEN** 准备同步的 ConceptStock 实体时
- **THEN** 系统计算 `sha256(f"{source}|{stock_third_code}|{stock_symbol or ''}")[:16]`
- **AND** 将哈希存储在 `content_hash` 字段中
- **AND** 哈希不包含 `concept_id`（因为新实体尚未持久化 id）

