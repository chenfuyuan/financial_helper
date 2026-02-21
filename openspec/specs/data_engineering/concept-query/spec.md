# Spec: 题材板块查询 (concept-query)

提供题材板块及其成分股的查询接口，支持按数据源过滤和详细的错误处理，确保 API 响应格式统一。

## Requirements

### Requirement: 查询题材板块列表

系统 SHALL 提供 API 端点获取题材板块列表，响应格式为 `ApiResponse[list[ConceptResponse]]`。

#### Scenario: 获取所有题材板块

- **WHEN** 用户请求 `GET /api/v1/data-engineering/concepts`
- **THEN** 系统返回数据库中的所有题材板块
- **AND** 响应包装在 `ApiResponse` 中，状态码为 `code=200`
- **AND** 每个题材包含：id、source、third_code、name、last_synced_at

#### Scenario: 按数据源过滤题材

- **WHEN** 用户请求 `GET /api/v1/data-engineering/concepts?source=AKSHARE`
- **THEN** 系统仅返回指定数据源的题材
- **AND** 排除其他数据源的题材

#### Scenario: 无题材数据存在

- **WHEN** 用户请求题材板块但尚未同步任何数据
- **THEN** 系统返回空列表，状态码为 `code=200`
- **AND** 响应为 `ApiResponse(code=200, data=[])`

#### Scenario: 无效的数据源参数

- **WHEN** 用户请求 `GET /api/v1/data-engineering/concepts?source=INVALID`
- **THEN** 系统返回 422 Unprocessable Entity 错误（FastAPI 验证）

### Requirement: 查询题材的成分股

系统 SHALL 提供 API 端点获取特定题材板块的成分股，响应格式为 `ApiResponse[list[ConceptStockResponse]]`。

#### Scenario: 获取题材成分股

- **WHEN** 用户请求 `GET /api/v1/data-engineering/concepts/{concept_id}/stocks`
- **THEN** 系统返回指定题材的所有 ConceptStock 关系
- **AND** 每个股票包含：id、concept_id、source、stock_third_code、stock_symbol、added_at

#### Scenario: 题材不存在

- **WHEN** 用户请求不存在的 concept_id 的成分股
- **THEN** 系统抛出 `ConceptNotFoundError`
- **AND** 全局异常处理器返回 404 Not Found，格式为 `ApiResponse(code=404, message=...)`

#### Scenario: 题材存在但无成分股

- **WHEN** 用户请求存在但无关联股票的题材的成分股
- **THEN** 系统返回空列表，状态码为 `code=200`
- **AND** 响应为 `ApiResponse(code=200, data=[])`

