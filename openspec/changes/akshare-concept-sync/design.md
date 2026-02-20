
## Context

金融助手系统的 `data_engineering` 模块目前仅支持 TuShare 数据源，缺少概念板块及成分股关联关系数据。本设计基于项目现有的 DDD + 整洁架构模式，新增 AKShare 数据源支持，实现概念板块数据的同步和查询功能。

参考的现有模式（代码级对齐）：
- `StockBasic` 聚合根 + `StockBasicRepository` 独立仓储接口
- `TuShareStockGateway` + `TuShareStockBasicMapper` 网关 / 映射
- `SyncStockBasic` Command + `SyncStockBasicHandler` 应用层编排
- `StockBasicModel` ORM 模型 + `StockBasicPersistenceMapper` 持久化映射
- `ExternalStockServiceError` 领域异常

## Goals / Non-Goals

**Goals:**
- 实现基于 AKShare 东方财富数据源的概念板块及成分股同步
- 采用基于哈希的两级精细增量同步策略（概念级 → 成分股级），最小化数据库写入
- 严格遵循现有 DDD + 整洁架构四层模式及项目开发规范
- 提供概念板块和成分股查询 HTTP API
- 实现与现有 `StockBasic` 的双重关联策略

**Non-Goals:**
- 不实现定时任务调度（仅提供 API 触发）
- 不实现概念板块行情数据、资金流、筹码分布等扩展数据同步
- 不实现分页查询（当前概念板块数量约数百条，数据量可控；后续按需扩展）
- 不实现多数据源概念板块并行（仅东方财富，但网关抽象层预留扩展性）

## Decisions

### 1. 领域模型设计

**决策**: `Concept` 为聚合根，`ConceptStock` 为独立实体（`Entity`），各自拥有独立 Repository。

**替代方案**: ① 将 ConceptStock 作为 Concept 聚合内部实体，仅通过 ConceptRepository 访问；② 扩展 StockBasic 添加概念标签字段。

**理由**:
- 概念板块是独立业务概念，天然具备聚合根特征
- 成分股生命周期依附于概念（级联删除），因此建模为 `Entity` 而非 `AggregateRoot`
- 同步场景需对成分股做细粒度批量增删，独立 Repository 更高效 — 遵循项目规范"批量操作等特殊场景允许模块仓储接口独立定义 ABC"
- 便于未来扩展概念板块的其他属性和关联

**Concept 聚合根（领域层）**:
```python
@dataclass(eq=False)
class Concept(AggregateRoot[int | None]):
    """概念板块聚合根。以 (source, third_code) 为逻辑唯一键，仅含业务属性。

    Attributes:
        id: 主键；新建未持久化时为 None。
        source: 数据来源（如 AKSHARE）。
        third_code: 第三方概念代码（如 BK0818）。
        name: 概念名称。
        content_hash: 基于业务字段的 SHA-256 摘要前16位，用于增量同步变更检测。
        last_synced_at: 最后同步时间。
    """
    id: int | None
    source: DataSource
    third_code: str
    name: str
    content_hash: str
    last_synced_at: datetime
```

**ConceptStock 实体（领域层）**:
```python
@dataclass(eq=False)
class ConceptStock(Entity[int | None]):
    """概念-股票关联实体。以 (concept_id, source, stock_third_code) 为逻辑唯一键。

    Attributes:
        id: 主键；新建未持久化时为 None。
        concept_id: 关联的 Concept.id。
        source: 数据来源。
        stock_third_code: 股票第三方代码（AKShare 原始代码，如 000001）。
        stock_symbol: 匹配后的 StockBasic.symbol（如 000001.SZ）；匹配失败为 None。
        content_hash: 基于业务字段的 SHA-256 摘要前16位。
        added_at: 关联添加时间。
    """
    id: int | None
    concept_id: int
    source: DataSource
    stock_third_code: str
    stock_symbol: str | None
    content_hash: str
    added_at: datetime
```

**内容哈希计算规则**:
- **Concept**: `sha256(f"{source}|{third_code}|{name}")[:16]`
- **ConceptStock**: `sha256(f"{source}|{stock_third_code}|{stock_symbol or ''}")[:16]`

> ⚠️ **关键修正**: 原草案 ConceptStock 哈希包含 `concept_id`。但新增概念的成分股在持久化前 `concept_id` 为 None，导致远端与本地哈希永远不匹配，增量对比逻辑失效。修正为仅用业务字段计算，同一概念下的成分股通过 parent concept 隐式关联。

**DataSource 枚举扩展**:
```python
class DataSource(StrEnum):
    TUSHARE = "TUSHARE"
    AKSHARE = "AKSHARE"  # 新增
```

### 2. 同步策略

**决策**: 基于哈希的两级增量同步（概念级 → 成分股级），整体单事务提交。

**替代方案**: ① 全量同步（每次删除重建）；② 混合策略（概念全量 + 成分股增量）；③ 按概念分批事务。

**理由**:
- 两级增量对比最小化数据库写入，数据质量和性能最优
- 整体单事务保证数据一致性（概念总量约数百条，单次同步数据量可控）
- 若未来数据量增长导致事务过大，可改为按概念分批事务（Migration Plan 预留改造点）

**同步流程（伪代码）**:
```
1. remote_concepts = gateway.fetch_concepts()
2. local_concepts  = concept_repo.find_all(source=AKSHARE)
3. 以 third_code 为键构建两侧 dict:
   remote_map = {c.third_code: c for c in remote_concepts}
   local_map  = {c.third_code: c for c in local_concepts}

4. 三路对比:
   a. 新增 (remote 有, local 无):
      → concept_repo.save(concept) → 获得 concept.id
      → fetch & save 成分股 (全量, 无需对比)
   b. 修改 (两侧都有, content_hash 不同):
      → 更新 concept 字段 → concept_repo.save(concept)
      → 二级成分股增量对比 (见步骤 5)
   c. 未变 (两侧都有, content_hash 相同):
      → 跳过, 仅更新 last_synced_at
   d. 删除 (remote 无, local 有):
      → concept_stock_repo.delete_by_concept_id(id)
      → concept_repo.delete(id)

5. 成分股二级增量对比 (仅对修改的概念):
   a. remote_stocks = gateway.fetch_concept_stocks(third_code)
   b. local_stocks  = concept_stock_repo.find_by_concept_id(concept_id)
   c. 以 stock_third_code 为键三路对比:
      - 新增: 尝试关联 StockBasic → concept_stock_repo.save()
      - 修改 (hash 不同): 更新 stock_symbol → concept_stock_repo.save()
      - 删除: concept_stock_repo.delete()

6. uow.commit()  # 整体单事务
7. 返回 SyncConceptsResult (各类计数 + 耗时)
```

> ⚠️ **关键修正**: 原草案对"修改概念"采用"清空旧成分股，重新获取并插入"的策略，与 proposal 要求的"基于哈希的精细增量同步"矛盾。修正为对修改概念也执行成分股级别的哈希对比，真正实现两级精细增量。

### 3. 数据关联策略（StockBasic 匹配）

**决策**: 双重关联 — 优先 symbol 前缀匹配，回退 third_code 匹配。

**替代方案**: ① 仅 symbol 匹配；② 仅 third_code 匹配。

**理由**:
- 提高关联成功率，兼容不同数据源的代码格式差异
- 即使关联失败也保留 `stock_third_code` 原始数据，不丢信息

**匹配算法**:
```
1. AKShare 返回股票代码 raw_code（如 "000001"）
2. 根据代码前缀推断交易所后缀:
   - 6 开头 → ".SH"（上海）
   - 0 或 3 开头 → ".SZ"（深圳）
   - 4 或 8 开头 → ".BJ"（北京）
   → 构造 candidate_symbol = raw_code + suffix（如 "000001.SZ"）
3. 在预加载的 symbol_map 中查找:
   a. 优先: symbol_map.get(candidate_symbol)
   b. 回退: third_code_map.get(candidate_symbol)
4. 匹配成功 → stock_symbol = candidate_symbol
5. 匹配失败 → stock_symbol = None, 记录 warning 日志
```

**批量优化**: 同步开始时**一次性预加载**所有 `StockBasic` 构建两个内存 dict:
- `symbol_map: dict[str, int]` — `{symbol: id}`
- `third_code_map: dict[str, int]` — `{third_code: id}`（source=TUSHARE）

避免逐条查询 StockBasic 造成 N+1 问题。

> ⚠️ **关键修正**: 原草案未说明 AKShare 股票代码格式与 StockBasic.symbol 的转换规则，也未提及 N+1 查询风险。补充了交易所后缀推断逻辑和批量预加载策略。

### 4. AKShare 网关实现

**决策**: 参考 `TuShareStockGateway` 模式，`asyncio.to_thread()` 包装同步调用。

**替代方案**: ① 寻找异步 AKShare 库；② 自行实现异步 HTTP 客户端调用东方财富接口。

**理由**:
- 与现有 TuShare 网关代码风格完全一致
- AKShare 官方库是同步的，包装是最稳妥方案
- 便于统一处理限流和错误

**ConceptGateway 接口（领域层 `domain/gateways/`）**:
```python
class ConceptGateway(ABC):
    """从外部数据源拉取概念板块及成分股数据。"""

    @abstractmethod
    async def fetch_concepts(self) -> list[Concept]:
        """获取所有概念板块列表。"""
        ...

    @abstractmethod
    async def fetch_concept_stocks(self, concept_third_code: str, concept_name: str) -> list[tuple[str, str]]:
        """获取指定概念的成分股列表。

        Args:
            concept_third_code: 概念第三方代码（如 BK0818）。
            concept_name: 概念名称（部分 AKShare 接口需要按名称查询）。

        Returns:
            [(stock_third_code, stock_name), ...] — 股票第三方代码和名称。
        """
        ...
```

**AkShareConceptGateway 实现（基础设施层 `infrastructure/gateways/`）**:
- 调用 `akshare.stock_board_concept_name_em()` → 概念板块列表 DataFrame
- 调用 `akshare.stock_board_concept_cons_em(symbol=concept_name)` → 成分股 DataFrame
- **延迟 import**: `import akshare` 放在方法内部（与 `TuShareStockGateway` 模式一致），避免启动时加载
- 异常统一捕获并包装为 `ExternalConceptServiceError`

**AkShareConceptMapper（基础设施层 `infrastructure/gateways/mappers/`）**:
- `rows_to_concepts(df)` → `list[Concept]`: DataFrame 转领域实体，计算 content_hash
- `rows_to_stock_tuples(df)` → `list[tuple[str, str]]`: DataFrame 转 (stock_third_code, stock_name)
- 字段缺失或格式异常抛 `ExternalConceptServiceError`

**限流**: 首版在 `fetch_concept_stocks` 循环中加 `asyncio.sleep(0.1)` 作为基础限流。后续根据实测 AKShare 限流策略调整参数或引入 Token Bucket。

### 5. 数据库表设计

**concept 表**:

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | int | PK, autoincrement | 主键 |
| source | varchar(32) | NOT NULL | 数据源枚举值 |
| third_code | varchar(32) | NOT NULL | 第三方概念代码 |
| name | varchar(100) | NOT NULL | 概念名称 |
| content_hash | varchar(16) | NOT NULL | SHA-256 前 16 位 |
| last_synced_at | timestamptz | NOT NULL | 最后同步时间 |
| created_at | timestamptz | NOT NULL, default now() | 创建时间 |
| updated_at | timestamptz | NOT NULL, default now(), onupdate now() | 更新时间 |
| version | int | NOT NULL, default 1 | 乐观锁 |

- **唯一键**: `UNIQUE(source, third_code)`

**concept_stock 表**:

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | int | PK, autoincrement | 主键 |
| concept_id | int | FK → concept.id ON DELETE CASCADE, NOT NULL | 关联概念 |
| source | varchar(32) | NOT NULL | 数据源枚举值 |
| stock_third_code | varchar(32) | NOT NULL | 股票第三方代码 |
| stock_symbol | varchar(32) | NULL | 匹配后的 StockBasic.symbol |
| content_hash | varchar(16) | NOT NULL | SHA-256 前 16 位 |
| added_at | timestamptz | NOT NULL | 关联添加时间 |
| created_at | timestamptz | NOT NULL, default now() | 创建时间 |
| updated_at | timestamptz | NOT NULL, default now(), onupdate now() | 更新时间 |
| version | int | NOT NULL, default 1 | 乐观锁 |

- **唯一键**: `UNIQUE(concept_id, source, stock_third_code)`
- **外键**: `concept_id → concept.id ON DELETE CASCADE`
- **索引**: `IX_concept_stock_symbol(stock_symbol)`, `IX_concept_stock_third_code(stock_third_code)`

> ⚠️ **关键修正**:
> 1. 原草案 `content_hash` 为 `varchar(64)`，实际 SHA-256 前 16 位只需 `varchar(16)`。
> 2. 原草案外键未指定级联删除。删除 Concept 时若不级联，ConceptStock 会违反外键约束。补充 `ON DELETE CASCADE`。

### 6. 仓储接口设计

**ConceptRepository（领域层 `domain/repositories/`）**:
```python
class ConceptRepository(ABC):
    """概念板块仓储接口。不 commit，由调用方 UnitOfWork 管理事务。"""

    @abstractmethod
    async def find_all(self, source: DataSource) -> list[Concept]: ...

    @abstractmethod
    async def find_by_id(self, concept_id: int) -> Concept | None: ...

    @abstractmethod
    async def find_by_third_code(self, source: DataSource, third_code: str) -> Concept | None: ...

    @abstractmethod
    async def save(self, concept: Concept) -> Concept:
        """保存概念（新增或更新）。返回含 id 的实体（新增时 DB 分配 id）。"""
        ...

    @abstractmethod
    async def delete(self, concept_id: int) -> None: ...

    @abstractmethod
    async def delete_many(self, concept_ids: list[int]) -> None: ...
```

**ConceptStockRepository（领域层 `domain/repositories/`）**:
```python
class ConceptStockRepository(ABC):
    """概念-股票关联仓储接口。不 commit，由调用方 UnitOfWork 管理事务。"""

    @abstractmethod
    async def find_by_concept_id(self, concept_id: int) -> list[ConceptStock]: ...

    @abstractmethod
    async def save_many(self, concept_stocks: list[ConceptStock]) -> None:
        """批量保存（新增或更新）。"""
        ...

    @abstractmethod
    async def delete_many(self, concept_stock_ids: list[int]) -> None: ...

    @abstractmethod
    async def delete_by_concept_id(self, concept_id: int) -> None:
        """删除指定概念的所有关联关系。"""
        ...
```

> ⚠️ **关键修正**:
> 1. 补充 `save_many` / `delete_many` 批量方法，避免逐条操作大量 DB round-trip。
> 2. `ConceptRepository.save()` 返回含 id 的 `Concept`，新增概念后需 id 来关联成分股。
> 3. 移除原草案的 `find_by_concept_and_stock`（成分股对比通过 `find_by_concept_id` + 内存 dict 过滤即可，减少仓储接口膨胀）。
> 4. 补充 `find_by_id` 供查询 API 的 404 校验使用。

### 7. 接口层设计

**HTTP 端点**:

| Method | Path | Handler | 说明 |
|--------|------|---------|------|
| POST | `/api/v1/data-engineering/concepts/sync` | `SyncConceptsHandler` | 触发概念同步 |
| GET | `/api/v1/data-engineering/concepts` | `GetConceptsHandler` | 查询概念列表 |
| GET | `/api/v1/data-engineering/concepts/{concept_id}/stocks` | `GetConceptStocksHandler` | 查询成分股 |

**Application 层 Command / Query**:
```python
@dataclass(frozen=True)
class SyncConcepts(Command):
    """触发一次概念板块同步。无参数。"""
    pass

@dataclass(frozen=True)
class GetConcepts(Query):
    """查询概念板块列表。"""
    source: DataSource | None = None

@dataclass(frozen=True)
class GetConceptStocks(Query):
    """查询指定概念的成分股。"""
    concept_id: int
```

**Response Models（Pydantic，接口层 `interfaces/api/`）**:
```python
class SyncConceptsResponse(BaseModel):
    total_concepts: int
    new_concepts: int
    modified_concepts: int
    deleted_concepts: int
    total_stocks: int
    new_stocks: int
    modified_stocks: int
    deleted_stocks: int
    duration_ms: int

class ConceptResponse(BaseModel):
    id: int
    source: str
    third_code: str
    name: str
    last_synced_at: datetime

class ConceptStockResponse(BaseModel):
    id: int
    concept_id: int
    source: str
    stock_third_code: str
    stock_symbol: str | None
    added_at: datetime
```

所有响应用 `ApiResponse[T]` 包装（与现有 `stock_basic_router.py` 模式一致）。

**依赖注入（`interfaces/dependencies.py`）**: 新增 `get_sync_concepts_handler()`、`get_get_concepts_handler()`、`get_get_concept_stocks_handler()` 三个工厂函数，参考现有 `get_sync_stock_basic_handler()` 模式组装依赖。

**模块注册**: 在 `module_registry.py` 的 `_collect_module_routers()` 中追加 `concept_router`。

### 8. 错误处理

新增领域异常（`domain/exceptions.py`）:
```python
class ExternalConceptServiceError(DomainException):
    """AKShare 概念板块数据源拉取或解析失败。"""

class ConceptNotFoundError(DomainException):
    """查询的概念板块不存在。"""
```

**异常处理策略**:
- `ExternalConceptServiceError`: Gateway 层捕获 AKShare 所有异常后包装抛出，Handler 不捕获，事务自动回滚
- `ConceptNotFoundError`: 查询成分股时 concept_id 不存在，接口层的全局异常处理器转 404
- 同步失败时 UoW 未 commit，事务自动回滚，无脏数据残留

### 9. 日志要点

遵循 `guide/development-conventions.md` 日志规范，关键打点：
- **Handler 入口**: info — 命令名
- **Handler 结束**: info — 同步结果摘要（new/modified/deleted 计数、耗时）
- **Gateway 请求前**: info — api_name、concept_third_code
- **Gateway 请求后**: info — 返回条数、是否为空
- **关联匹配失败**: warning — stock_third_code、candidate_symbol
- **异常**: error — 业务上下文 + exc_info=True

## Risks / Trade-offs

| Risk | Impact | Mitigation |
|------|--------|------------|
| AKShare 接口变更或失效 | 同步中断 | 网关抽象层隔离；Mapper 集中转换逻辑，接口变更只改 Mapper |
| 逐个获取成分股耗时长 | 同步慢（约 500 概念 × 0.1s ≈ 50s） | 首版可接受；后续可改 `asyncio.gather` + Semaphore 并发 |
| 整体单事务数据量过大 | 长事务锁竞争 | 当前数据量可控；代码预留分批事务改造点 |
| 股票代码格式不匹配 | 关联失败率高 | 交易所后缀推断 + 预加载匹配；失败仍保存原始数据 + warning 日志 |
| 并发触发同步 | 唯一键冲突 / 数据不一致 | 首版不做并发控制（API 手动触发频率低）；后续可加 DB advisory lock |
| AKShare 请求限流 | 被封 IP | 首版 sleep(0.1) 基础限流；后续实测后引入 Token Bucket |

## Migration Plan

1. `pyproject.toml` 新增 `akshare>=1.12.0` 依赖
2. `DataSource` 枚举新增 `AKSHARE`
3. 创建 Alembic 迁移脚本（`concept`、`concept_stock` 两张表，含唯一键、外键、索引）
4. 按 DDD 层级顺序实现: Domain → Infrastructure → Application → Interfaces
5. 在 `module_registry.py` 注册 `concept_router`
6. 编写单元测试（Gateway Mapper、Hash 计算、匹配算法）和集成测试（Repository CRUD、Handler 同步流程）
7. 执行数据库迁移，API 端到端测试

**回滚策略**: 代码 revert + `alembic downgrade`

## Open Questions

- AKShare `stock_board_concept_cons_em` 的实际限流阈值？需实测后调整 sleep 间隔或引入 Token Bucket
- 概念板块数据更新频率？建议文档中标注推荐同步周期（如每日一次）

