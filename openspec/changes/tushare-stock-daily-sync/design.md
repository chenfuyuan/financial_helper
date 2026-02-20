## Context

当前系统已在 `data_engineering` 模块实现了股票基础信息同步（StockBasic）功能，遵循 DDD + 整洁架构模式。本变更在此基础上新增股票日线行情数据同步功能，需要从 TuShare 获取 daily、adj_factor、daily_basic 三个接口的数据并组装为完整的 `StockDaily` 实体。

**前置依赖：** 历史同步需要从 `StockBasicRepository` 获取股票列表及上市日期，因此本变更依赖 StockBasic 同步功能已就绪。

**约束条件：**
- 遵循现有项目架构约定（见 `guide/architecture.md`、`guide/development-conventions.md`）
- 领域实体仅含业务属性，不含审计字段（`created_at`/`updated_at`/`version`）
- TuShare API 限流：每分钟不超过 200 次调用
- 使用 PostgreSQL 作为主数据库

**相关文件：**
- 现有实现参考：`src/app/modules/data_engineering/` 下的 StockBasic 相关代码
- 数据库迁移示例：`migrations/versions/20260220_0000_add_stock_basic_table.py`

## Goals / Non-Goals

**Goals:**
- 实现股票日线历史数据同步功能，支持从股票上市日期开始同步，支持断点续传（查本地最新日期后增量拉取）
- 实现股票日线增量同步功能，支持按交易日同步
- 实现失败记录重试功能，支持最大重试次数限制
- 支持 TuShare API 限流控制（Token Bucket）
- 以 (source, third_code, trade_date) 为唯一键做幂等 upsert
- daily_basic 部分字段对新股/停牌股允许为 None

**Non-Goals:**
- 不实现定时任务自动同步（待后续 foundation 模块 scheduler 完善后再添加）
- 不实现数据质量检测（后续可由 data_quality 子模块负责）
- 不实现数据分析逻辑（只负责数据供给，不做分析）
- 不实现交易日历判断（增量同步默认昨天自然日，由调用方负责判断交易日）
- 不实现并发同步锁（当前由调用方保证不并发触发，后续可加分布式锁）

## Decisions

### 决策 1：数据组装策略
**选择：** 完全组装为一个 StockDaily 实体，存储在一张数据库表中

**备选方案：**
- 方案 A：完全组装为一个实体（已选）
  - 优点：查询效率高，数据使用方便
  - 缺点：表字段较多（约 30 个），daily_basic 字段需允许 NULL
- 方案 B：主从实体结构，三张表
  - 优点：数据结构更清晰，符合范式
  - 缺点：需要关联查询，性能稍差
- 方案 C：三个独立实体，应用层组装
  - 优点：灵活性高
  - 缺点：使用复杂

**决策理由：** 股票日线数据通常是一起使用的，组装为一个实体可以提高查询效率和使用便利性。daily_basic 字段允许 NULL 以兼容新股/停牌股数据缺失。

---

### 决策 2：网关接口设计 — 独立抽象接口
**选择：** `StockDailyGateway` 作为独立 ABC，不扩展 `StockGateway`；统一封装为两个方法，内部调用三个 TuShare 接口

**备选方案：**
- 方案 A：独立接口 + 统一封装（已选）
  - 优点：SRP — 日线网关职责独立；接口简洁，组装逻辑内聚在 Gateway 实现类中
  - 缺点：多一个抽象类
- 方案 B：扩展 StockGateway，在其上追加方法
  - 优点：复用同一个抽象
  - 缺点：违反 SRP，StockGateway 会不断膨胀；StockBasic 和 StockDaily 的实现耦合
- 方案 C：暴露三个独立接口，应用层组装
  - 优点：Gateway 简单
  - 缺点：应用层需要处理数据源特有的组装逻辑，泄露基础设施细节

**决策理由：** 按 SRP 原则，每个网关接口只负责一种数据类型的拉取。三个 TuShare 接口的组装是数据源相关逻辑，应封装在 Gateway 实现类内部，保持 Domain 层接口简洁。参数使用领域类型 `date` 而非字符串。

---

### 决策 3：历史同步错误处理策略
**选择：** 单只股票失败不阻塞，记录到失败表（含日期范围），每只股票独立事务

**备选方案：**
- 方案 A：单只失败不阻塞，记录失败表（已选）
  - 优点：整体同步进度不受单只股票影响；失败记录含 start_date/end_date 支持精确重试
  - 缺点：需要额外的失败表和重试逻辑
- 方案 B：单只失败即整体失败
  - 优点：简单
  - 缺点：历史同步可能因单只股票失败而停滞

**决策理由：** 历史同步涉及大量股票，因单只股票失败而整体回滚不合理，采用独立事务 + 失败记录的方式更健壮。失败记录中包含日期范围，重试时可精确定位。

---

### 决策 4：增量同步错误处理策略
**选择：** 整体事务，失败即抛出异常并回滚

**备选方案：**
- 方案 A：整体事务，失败即回滚（已选）
  - 优点：数据一致性好，简单
  - 缺点：单只失败影响整体
- 方案 B：与历史同步相同策略
  - 优点：策略统一
  - 缺点：增量同步数据量小，没必要

**决策理由：** 增量同步只涉及一个交易日的数据，数据量相对较小，采用整体事务更简洁且保证数据一致性。

---

### 决策 5：TuShare 限流控制
**选择：** 在 Gateway 实现类中使用 Token Bucket 控制调用频率

**备选方案：**
- 方案 A：Gateway 内 Token Bucket（已选）
  - 优点：逻辑内聚，调用方无需关心；相比固定 sleep 更精确，不浪费等待时间
  - 缺点：Gateway 实现稍复杂
- 方案 B：每次调用前固定 `asyncio.sleep(0.3)`
  - 优点：实现极简
  - 缺点：不够精确，低频调用时浪费等待时间；突发调用可能超限
- 方案 C：使用 FOUNDATION 层的限流服务
  - 优点：复用基础设施
  - 缺点：当前 FOUNDATION 层尚未提供此服务，过度设计

**决策理由：** Token Bucket 在精确度和实现复杂度间取得较好平衡。容量 200、每分钟补充 200 token。后续如有更复杂需求再抽取到 FOUNDATION 层。

---

### 决策 6：历史同步断点续传策略
**选择：** 同步前查询本地最新 `trade_date`，仅拉取增量数据

**备选方案：**
- 方案 A：查本地最新日期后增量拉取（已选）
  - 优点：中断后重启自动从断点继续，避免重复拉取；实现简单（一个 Repository 方法）
  - 缺点：需新增 `get_latest_trade_date` 仓储方法
- 方案 B：额外维护同步进度表
  - 优点：进度信息更详细
  - 缺点：引入新表和新实体，过度设计
- 方案 C：每次全量拉取，依赖 upsert 幂等
  - 优点：无需额外逻辑
  - 缺点：浪费大量 API 调用和时间

**决策理由：** 利用已有数据即可判断同步进度（本地最新日期 + 1 天 = 下次起点），无需额外进度表。配合 upsert 幂等性，即使有少量重叠也不会产生数据错误。

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| TuShare API 限流导致历史同步耗时长（5000 股 × 3 接口/股 ≈ 15000 次 API 调用） | Token Bucket 限流 + 断点续传（中断后从上次位置继续）；后续可考虑多 token 轮询 |
| 历史数据同步中途中断 | 断点续传：每只股票同步前查本地最新日期，从次日开始；每只股票独立事务，已完成的不受影响 |
| 单表字段多（约 30 列）可能影响查询性能 | 合理设计索引（唯一索引 + trade_date 索引）；后续可考虑 PostgreSQL 表分区（按 trade_date 月份） |
| daily_basic 部分字段对新股/停牌股为空 | daily_basic 字段设为 nullable，Mapper 容许 None |
| 增量同步 fetch_daily_all_by_date 数据量超过 TuShare 单次上限 | Gateway 实现内部处理分页，循环拉取直至数据完整 |
| 并发触发同一同步任务可能导致数据竞争 | 当前由调用方保证不并发触发；upsert 幂等性保证最终一致；后续可加分布式锁 |
| 数据库迁移失败 | 编写迁移测试；Alembic 支持回滚（downgrade） |

## Migration Plan

1. 创建数据库迁移脚本，添加 `stock_daily` 表（含唯一约束和 trade_date 索引）和 `stock_daily_sync_failure` 表
2. 部署数据库迁移
3. 实现 Domain 层代码：`StockDaily` 实体、`StockDailySyncFailure` 实体、`StockDailyGateway` 接口、`StockDailyRepository` 接口（含 `get_latest_trade_date`）、`StockDailySyncFailureRepository` 接口
4. 实现 Infrastructure 层代码：`TuShareStockDailyGateway`（含 Token Bucket 限流 + 分页）、Gateway Mapper（含 daily_basic nullable 处理）、`SqlAlchemyStockDailyRepository`、`SqlAlchemyStockDailySyncFailureRepository`、ORM 模型、Persistence Mapper
5. 实现 Application 层代码：三个 Command + Handler（`SyncStockDailyHistory` 需注入 `StockBasicRepository`）
6. 实现 Interface 层代码：HTTP 路由、请求/响应 Pydantic 模型、模块 `dependencies.py` 更新
7. 在 `module_registry.py` 注册新路由
8. 编写测试：单元测试（Mapper、Handler）、集成测试（Repository upsert + get_latest_trade_date）
9. 部署代码

**回滚策略：**
- 数据库迁移回滚：`alembic downgrade -1`
- 代码回滚：`git revert`

## Open Questions

1. **TuShare adj_factor 按 trade_date 查询是否有数量上限？** — 需实测确认是否需要分页处理
2. **历史同步 HTTP 接口长时间运行（可能数小时）是否需要改为异步任务模式？** — 当前阶段同步调用可接受，但 HTTP 超时需调用方配合设置较大 timeout；后续 scheduler 就绪后改为异步任务
3. **是否需要在 StockBasicRepository 新增 `find_all_listed()` 方法？** — 或者复用现有查询方法筛选 status=LISTED
