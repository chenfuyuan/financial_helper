# Spec: 股票基础信息同步 (stock-basic-sync)

从外部数据源拉取 A 股股票基础信息并写入本地持久化，支持通过 HTTP 按需触发；持久化以 (source, third_code) 为唯一键做幂等 upsert。

## ADDED Requirements

### Requirement: 同步可由 HTTP 触发

系统 SHALL 提供管理端接口，允许调用方通过 HTTP POST 触发一次股票基础信息同步。

#### Scenario: 调用同步接口

- **WHEN** 客户端向 `POST /data-engineering/stock-basic/sync` 发起请求
- **THEN** 系统执行一次同步用例（从外部网关拉取数据并写入本地仓储），并在完成后返回响应

### Requirement: 成功时返回同步结果摘要

同步成功完成后，系统 SHALL 在响应中返回本次同步的条数；MAY 返回耗时等辅助信息。

#### Scenario: 同步成功返回条数

- **WHEN** 同步执行成功且外部数据源返回了 N 条有效记录并已全部写入本地
- **THEN** 客户端收到的成功响应中 MUST 包含本次同步的条数（与 N 一致或为实际写入/更新的条数）

#### Scenario: 同步成功响应格式

- **WHEN** 同步执行成功
- **THEN** 客户端收到 2xx 状态码及结构化响应体（至少包含同步条数字段）

### Requirement: 外部数据源失败时不提交并返回错误

当从外部数据源拉取失败（如网络错误、鉴权失败、限流）时，系统 SHALL 不向本地持久化提交任何变更，并 SHALL 向客户端返回表示失败的错误响应。

#### Scenario: 外部源拉取失败

- **WHEN** 同步执行过程中外部数据网关抛出异常（如网络或鉴权错误）
- **THEN** 本地数据库不发生提交（事务回滚），客户端收到表示服务器/外部依赖错误的响应（如 5xx 或统一错误格式）

### Requirement: 以 (source, third_code) 为唯一键幂等持久化

系统 SHALL 将每条股票基础信息的持久化唯一键定义为 (source, third_code)。同一 (source, third_code) 的多次同步 SHALL 表现为 upsert：已存在则更新字段，不存在则插入；多次调用后最终持久化状态一致（幂等）。

#### Scenario: 首次同步插入

- **WHEN** 同步执行且某条记录的 (source, third_code) 在本地尚不存在
- **THEN** 该条记录被插入本地表，且包含 source、third_code、symbol、name、market、list_date、status 等约定字段

#### Scenario: 再次同步更新

- **WHEN** 同步执行且某条记录的 (source, third_code) 在本地已存在
- **THEN** 该条记录对应行被更新（如 name、market、status 等），唯一键 (source, third_code) 不变，最终仅保留一行

#### Scenario: 多次同步结果一致

- **WHEN** 在相同外部数据源结果下，连续两次成功执行同步
- **THEN** 第二次执行后本地表中与本次数据对应的行集及关键字段值与第一次执行后一致（无重复行、无多余变更）

### Requirement: 持久化记录包含基础字段与必要业务字段

系统 SHALL 持久化的股票基础信息记录包含项目规定的**基础字段**：id、created_at、updated_at、version；并包含以下业务字段：来源 (source)、第三方代码 (third_code)、代码 (symbol)、名称 (name)、市场 (market)、上市日期 (list_date)、状态 (status)；MAY 包含 area、industry 等。

#### Scenario: 成功同步后记录可查且字段完整

- **WHEN** 同步成功完成且外部源返回了至少一条包含 symbol、name、market、list_date、status 的数据
- **THEN** 本地可查询到对应 (source, third_code) 的记录，且该记录包含基础字段（id、created_at、updated_at、version）以及 symbol、name、market、list_date、status 等业务字段，与同步源语义一致

### Requirement: 单条解析失败则整次同步失败

一次同步对应外部接口返回的一批数据。当该批数据中任一条解析失败（如日期非法、必填缺失）时，系统 SHALL 视为本次同步失败：不向本地持久化提交任何变更，并 SHALL 向客户端返回错误响应；整批数据必须全部成功解析并落库后，同步才视为成功。

#### Scenario: 任一条解析失败则同步失败

- **WHEN** 外部数据源返回的一批数据中存在至少一条无法正确解析的记录（如 list_date 非法、必填字段缺失）
- **THEN** 系统不写入任何记录，事务不提交，客户端收到表示失败的错误响应（如 5xx 或统一错误格式）
