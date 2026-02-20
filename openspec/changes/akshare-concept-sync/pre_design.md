
# 预设计文档：AkShare 概念板块同步

## 1. 总体架构

遵循现有 `data_engineering` 模块的 DDD + 整洁架构模式：
- **Domain Layer**: `Concept` 聚合根、`ConceptStock` 实体、`ConceptGateway` 接口、`ConceptRepository` 接口、`ConceptStockRepository` 接口
- **Application Layer**: 同步 Command + Handler（基于哈希的精细增量同步）
- **Infrastructure Layer**: `AkShareConceptGateway` 实现、`SqlAlchemyConceptRepository`、`SqlAlchemyConceptStockRepository`、数据库模型、Gateway Mapper
- **Interface Layer**: HTTP 路由

## 2. 数据模型设计

### Concept 实体（领域层）

概念板块聚合根。遵循项目规范：**仅含业务属性，不含审计字段**。

- 标识字段：`id: int | None`、`source: DataSource`、`third_code: str`（东方财富概念代码，如 BK0818）
- 业务字段：`name: str`（概念名称）、`content_hash: str`（内容哈希，用于增量对比）、`last_synced_at: datetime`
- 唯一约束：`(source, third_code)`

### ConceptStock 实体（领域层）

概念-股票关联实体。

- 标识字段：`id: int | None`、`concept_id: int`（关联 Concept.id）、`source: DataSource`、`stock_third_code: str`（股票第三方代码）
- 业务字段：`stock_symbol: str | None`（股票 symbol，用于关联 StockBasic）、`content_hash: str`（内容哈希）、`added_at: datetime`
- 唯一约束：`(concept_id, source, stock_third_code)`
- 双重关联策略：优先通过 `stock_symbol` 匹配 `StockBasic.symbol`，回退通过 `(source, stock_third_code)` 匹配

### DataSource 枚举扩展

新增 `AKSHARE = "AKSHARE"`。

## 3. 网关接口设计

### ConceptGateway（抽象接口）

```python
class ConceptGateway(ABC):
    """从外部数据源拉取概念板块及成分股数据。"""

    @abstractmethod
    async def fetch_concepts(self) -&gt; list[Concept]:
        """获取所有概念板块列表。"""

    @abstractmethod
    async def fetch_concept_stocks(self, concept_third_code: str) -&gt; list[tuple[str, str]]:
        """获取指定概念板块的成分股列表，返回 (stock_third_code, stock_symbol)。"""
```

### 封装逻辑说明（AkShareConceptGateway 实现）

- **数据源**：东方财富（East Money）接口
- **核心接口**：
  - `stock_board_concept_name_em()` - 获取概念板块列表
  - `stock_board_concept_cons_em(symbol)` - 获取概念成分股
- **异步包装**：使用 `asyncio.to_thread()` 包装同步的 AKShare 调用
- **限流**：考虑实现 Token Bucket 限流（待实测 AKShare 限流策略）
- **Mapper**：`AkShareConceptMapper` 负责 API 响应到领域实体的转换
- **股票代码处理**：处理 AKShare 返回的股票代码格式，匹配 `StockBasic` 的格式

## 4. 仓储接口设计

### ConceptRepository

```python
class ConceptRepository(ABC):
    @abstractmethod
    async def find_all(self, source: DataSource) -&gt; list[Concept]:
        """查询指定数据源的所有概念板块。"""

    @abstractmethod
    async def find_by_third_code(self, source: DataSource, third_code: str) -&gt; Concept | None:
        """通过第三方代码查询概念板块。"""

    @abstractmethod
    async def save(self, concept: Concept) -&gt; None:
        """保存概念板块（新增或更新）。"""

    @abstractmethod
    async def delete(self, concept_id: int) -&gt; None:
        """删除概念板块及其关联关系。"""
```

### ConceptStockRepository

```python
class ConceptStockRepository(ABC):
    @abstractmethod
    async def find_by_concept_id(self, concept_id: int) -&gt; list[ConceptStock]:
        """查询指定概念的所有成分股关联。"""

    @abstractmethod
    async def find_by_concept_and_stock(
        self, concept_id: int, source: DataSource, stock_third_code: str
    ) -&gt; ConceptStock | None:
        """通过概念和股票查询关联关系。"""

    @abstractmethod
    async def save(self, concept_stock: ConceptStock) -&gt; None:
        """保存概念-股票关联（新增或更新）。"""

    @abstractmethod
    async def delete(self, concept_stock_id: int) -&gt; None:
        """删除概念-股票关联。"""

    @abstractmethod
    async def delete_by_concept_id(self, concept_id: int) -&gt; None:
        """删除指定概念的所有关联关系。"""
```

## 5. 应用层设计

### SyncConcepts Command

基于哈希的精细增量同步：

- 参数：无
- 依赖：`ConceptGateway`、`ConceptRepository`、`ConceptStockRepository`、`StockBasicRepository`、`UnitOfWork`
- 流程：
  1. 从 AKShare 获取所有概念板块列表
  2. 查询数据库现有概念板块（按 source 过滤）
  3. 对比两组概念板块（通过 `content_hash`）：
     - **新增概念**：插入 Concept，获取成分股，插入 ConceptStock
     - **修改概念**：更新 Concept，清空旧成分股，重新获取并插入
     - **删除概念**：删除 Concept 及关联的 ConceptStock
  4. 对每个（新增或修改的）概念：
     a. 获取成分股列表
     b. 查询数据库现有该概念的成分股
     c. 对比成分股（通过 `content_hash`）：
        - **新增关联**：尝试关联 StockBasic，插入 ConceptStock
        - **修改关联**：更新 ConceptStock
        - **删除关联**：删除 ConceptStock
  5. 整体事务或按概念分批事务（待决定）
- 哈希计算：
  - Concept: `hash(source + third_code + name)`
  - ConceptStock: `hash(concept_id + source + stock_third_code + stock_symbol)`
- 返回：`SyncConceptsResult(total_concepts, new_concepts, modified_concepts, deleted_concepts, total_stocks, new_stocks, modified_stocks, deleted_stocks)`

## 6. 接口层设计

### HTTP 端点

- `POST /data-engineering/concepts/sync` — 触发概念板块同步
  - 请求体：无
  - 响应：`ApiResponse[SyncConceptsResult]`
- `GET /data-engineering/concepts` — 获取概念板块列表
  - 查询参数：`source: DataSource | None`（可选过滤）
  - 响应：`ApiResponse[list[Concept]]`
- `GET /data-engineering/concepts/{concept_id}/stocks` — 获取指定概念的成分股
  - 响应：`ApiResponse[list[ConceptStock]]`

### 定时任务

暂不实现，仅提供 API 接口调用。

## 7. 数据库设计

### concept 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键，自增 |
| source | varchar(32) | 数据源 |
| third_code | varchar(32) | 第三方概念代码 |
| name | varchar(100) | 概念名称 |
| content_hash | varchar(64) | 内容哈希 |
| last_synced_at | timestamptz | 最后同步时间 |
| created_at | timestamptz | 创建时间 |
| updated_at | timestamptz | 更新时间 |
| version | int | 乐观锁 |

**唯一键**: `(source, third_code)`

### concept_stock 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int | 主键，自增 |
| concept_id | int | 关联 concept.id |
| source | varchar(32) | 数据源 |
| stock_third_code | varchar(32) | 股票第三方代码 |
| stock_symbol | varchar(32) | 股票 symbol（可空） |
| content_hash | varchar(64) | 内容哈希 |
| added_at | timestamptz | 添加时间 |
| created_at | timestamptz | 创建时间 |
| updated_at | timestamptz | 更新时间 |
| version | int | 乐观锁 |

**唯一键**: `(concept_id, source, stock_third_code)`
**外键**: `concept_id` → `concept.id`
**索引**: `stock_symbol`, `stock_third_code`

## 8. 依赖更新

- `pyproject.toml` 新增 `akshare&gt;=1.12.0`

## 9. 错误处理

- `ExternalConceptServiceError`: AKShare 调用失败
- `ConceptSyncError`: 同步过程中的业务错误
- 参考现有错误处理模式

