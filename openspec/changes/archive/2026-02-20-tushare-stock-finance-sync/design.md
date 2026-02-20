## Context

我们需要获取 A 股上市公司的财务指标数据（Tushare `fina_indicator` 接口），用于后续的量化分析、基本面选股及财务健康度监控。目前系统已支持股票基础信息（`stock_basic`）和每日行情数据（`stock_daily`）的同步，但缺失关键的财务基本面数据。

### 外部 API 特性与约束

以下是 **Tushare `fina_indicator`** 接口的关键约束（**当前积分等级：2000**），它们直接决定了本次设计的核心架构：

| 约束项 | 描述 |
|:---|:---|
| **查询维度** | **仅支持按单只股票 (`ts_code`) 查询**。按 `ann_date` 查全市场需要 `fina_indicator_vip`（5000积分），当前不可用 |
| **单次返回上限** | 每次请求最多返回 **100 条**记录 |
| **频控** | **200次/分钟** |
| **数据粒度** | 每条记录以 `ts_code` + `end_date` (报告期) + `ann_date` (公告日期) 标识 |
| **数据特点** | 同一 `(ts_code, end_date)` 可能因财报修正而出现多条不同 `ann_date` 的记录 |

> [!IMPORTANT]
> 当前仅有 2000 积分，**不可使用 `fina_indicator_vip`**。所有同步流程必须基于按 `ts_code` 逐只查询的标准接口设计。
> 增量同步改为：遍历全市场股票，利用本地已有的最新 `end_date` 做断点续传，仅拉取新增报告期的数据。

## Goals / Non-Goals

**Goals:**
- 实现对全市场所有已知股票的历史财务指标的全量同步（按 `ts_code` 逐只遍历）。
- 实现基于单只股票 `third_code` 的历史数据修复/同步。
- 实现增量同步：遍历全市场股票，利用本地已有的最新 `end_date` 做断点续传，仅拉取新增的财务指标数据，用于 Daily Scheduler 触发。
- 复用现有 `TokenBucket` 令牌桶限流机制，遵守 Tushare 200次/分钟频控。
- 在全量同步过程中，以进程级内存 `Set` 实现防重，避免同一运行时内的重复拉取。
- 所有数据入库采用 Upsert 策略，以数据库唯一约束 `(source, third_code, end_date)` 为冲突键。

**Non-Goals:**
- 不引入重型外部状态中间件（如 Redis）或专门的同步任务状态持久化表。
- 不提供查询同步进度、停止同步任务等复杂管理 API。
- 不保留财报修正的历史版本（以最新数据无条件覆盖）。
- 不实现跨进程的断点续传（进程重启后全量同步从零开始，通过 Upsert 保证幂等）。

## Decisions

### 1. 唯一键与冲突处理策略

- **唯一键**: `(source, third_code, end_date)`
  - `source`: 数据来源（`DataSource.TUSHARE`）。
  - `third_code`: 对应 Tushare 的 `ts_code`。
  - `end_date`: 报告期截止日期（如 `20231231`），**而非 `ann_date`**。
- **Rationale**: 每只股票每个报告期只有一份最终的财务指标。如果公司修正了同一期的财报（不同 `ann_date` 发布），我们只关心最新一次的数值，因此以 `end_date` 为粒度做 Upsert，新数据无条件覆盖旧数据。`ann_date` 作为普通业务字段保存，记录"最近一次公告日期"。
- **Alternatives**: 以 `(source, third_code, end_date, ann_date)` 为唯一键保留所有修正版本。但这会带来查询复杂度增加（取最新版时需额外逻辑），且与当前 proposal 中"不保留修正前旧版本"的非功能需求矛盾。

### 2. 状态存储选型：内存缓存 (In-Memory)

- **Rationale**: 为保持架构极简，全量同步时在应用生命周期内以 `Set[str]` 记录已处理的 `ts_code`，防止同一运行时内重复拉取。
- **行为预期**: 如果进程中途崩溃重启，全量同步将从零开始，已入库数据通过 Upsert 幂等覆盖，不会产生数据不一致。
- **Alternatives**: 持久化入 DB（如 `sync_task_status` 表）。但鉴于全量同步只在初次或极少数修复场景执行，可接受重启归零的妥协。

### 3. 分页/分批策略

- **单股票拉取**: Tushare `fina_indicator` 按 `ts_code` 查询时单次返回最多 100 条。一般上市公司的历史财报条数不会超过 100 条（按季度算，25年 × 4季度 = 100条），但对于上市时间极长的公司，需要通过 `start_date` / `end_date` 参数分页。实现时采用 **检测式分页**：如果单次返回恰好 100 条，则视为可能存在更多数据，自动以返回结果中最早的 `end_date` 作为新的 `end_date` 再次请求，直到返回不足 100 条为止。

### 4. 增量同步策略（无 VIP 接口约束下）

由于无法按 `ann_date` 查询全市场数据，增量同步采用 **逐股票断点续传** 策略：

1. 遍历全市场股票列表。
2. 对每只股票，从 `FinancialIndicatorRepository` 查询本地已有的最新报告期 `end_date`。
3. 以该 `end_date` 的下一天作为 `start_date`，调用 `fina_indicator` 拉取新增数据。
4. 如果本地无数据（返回 `None`），则拉取全部历史。

与全量同步的区别在于：增量同步利用本地已有的 `end_date` 避免重复拉取历史数据，**大幅减少 API 调用次数**。对于已完成全量同步的系统，增量同步时大部分股票只需要 1 次 API 调用（甚至 0 次，若已是最新）。

### 5. API / 交互接口设计：最小化同步接口

- **Rationale**: 仅开发用于触发数据拉取的 Command/Handler：
  1. **全量同步** (`SyncFinanceIndicatorFull`): 遍历全市场，按单只股票逐一拉取全部历史数据（不看本地已有数据）。
  2. **按 `third_code` 单股票同步** (`SyncFinanceIndicatorByStock`): 拉取指定股票的全部历史财务指标。
  3. **增量同步** (`SyncFinanceIndicatorIncrement`): 遍历全市场，利用本地最新 `end_date` 做断点续传，仅拉取新增数据。
- **Alternatives**: 做完整的任务控制 API（启动、暂停、取消等），引入了不必要的设计复杂度。

## Module Structure

```
data_engineering/
├── domain/
│   ├── entities/
│   │   └── financial_indicator.py          [NEW] 财务指标实体
│   ├── gateways/
│   │   └── financial_indicator_gateway.py  [NEW] 抽象网关接口
│   └── repositories/
│       └── financial_indicator_repository.py [NEW] 抽象仓储接口
├── application/
│   └── commands/
│       ├── sync_finance_indicator_full.py           [NEW] Command + Result
│       ├── sync_finance_indicator_full_handler.py   [NEW] 全量同步 Handler
│       ├── sync_finance_indicator_by_stock.py       [NEW] Command + Result
│       ├── sync_finance_indicator_by_stock_handler.py [NEW] 单股票同步 Handler
│       ├── sync_finance_indicator_increment.py      [NEW] Command + Result
│       └── sync_finance_indicator_increment_handler.py [NEW] 增量同步 Handler
├── infrastructure/
│   ├── gateways/
│   │   ├── tushare_finance_indicator_gateway.py [NEW] Tushare 实现
│   │   └── mappers/
│   │       └── tushare_finance_indicator_mapper.py [NEW] 原始数据映射器
│   ├── models/
│   │   └── financial_indicator_model.py         [NEW] SQLAlchemy ORM 模型
│   └── repositories/
│       ├── sqlalchemy_financial_indicator_repository.py [NEW] 仓储实现
│       └── mappers/
│           └── financial_indicator_persistence_mapper.py [NEW] 持久化映射器
└── interfaces/
    ├── api/
    │   └── sync_router.py                       [MODIFY] 新增触发端点
    └── dependencies.py                          [MODIFY] 注册新 Handler 依赖
```

## Data Structures

### Domain Entity: `FinancialIndicator`

```python
@dataclass(eq=False)
class FinancialIndicator(Entity[int | None]):
    """财务指标实体。(source, third_code, end_date) 为逻辑唯一键。"""
    id: int | None
    source: DataSource
    third_code: str          # ts_code
    ann_date: date | None    # 公告日期（最近一次）
    end_date: date           # 报告期截止日（唯一键组成部分）

    # 核心指标（Decimal | None，因部分字段可能缺失）
    eps: Decimal | None                    # 基本每股收益
    dt_eps: Decimal | None                 # 稀释每股收益
    total_revenue_ps: Decimal | None       # 每股营业总收入
    revenue_ps: Decimal | None             # 每股营业收入
    capital_rese_ps: Decimal | None        # 每股资本公积
    surplus_rese_ps: Decimal | None        # 每股盈余公积
    undist_profit_ps: Decimal | None       # 每股未分配利润
    extra_item: Decimal | None             # 非经常性损益
    profit_dedt: Decimal | None            # 扣除非经常性损益后的净利润
    gross_margin: Decimal | None           # 毛利
    current_ratio: Decimal | None          # 流动比率
    quick_ratio: Decimal | None            # 速动比率
    cash_ratio: Decimal | None             # 保守速动比率
    ar_turn: Decimal | None                # 应收账款周转率
    ca_turn: Decimal | None                # 流动资产周转率
    fa_turn: Decimal | None                # 固定资产周转率
    assets_turn: Decimal | None            # 总资产周转率
    op_income: Decimal | None              # 经营活动净收益
    ebit: Decimal | None                   # 息税前利润
    ebitda: Decimal | None                 # 息税折旧摊销前利润
    fcff: Decimal | None                   # 企业自由现金流量
    fcfe: Decimal | None                   # 股权自由现金流量
    current_exint: Decimal | None          # 无息流动负债
    noncurrent_exint: Decimal | None       # 无息非流动负债
    interestdebt: Decimal | None           # 带息债务
    netdebt: Decimal | None                # 净债务
    tangible_asset: Decimal | None         # 有形资产
    working_capital: Decimal | None        # 营运资金
    networking_capital: Decimal | None     # 营运流动资本
    invest_capital: Decimal | None         # 全部投入资本
    retained_earnings: Decimal | None      # 留存收益
    diluted2_eps: Decimal | None           # 期末摊薄每股收益
    bps: Decimal | None                    # 每股净资产
    ocfps: Decimal | None                  # 每股经营活动产生的现金流量净额
    retainedps: Decimal | None             # 每股留存收益
    cfps: Decimal | None                   # 每股现金流量净额
    ebit_ps: Decimal | None                # 每股息税前利润
    fcff_ps: Decimal | None                # 每股企业自由现金流量
    fcfe_ps: Decimal | None                # 每股股东自由现金流量
    netprofit_margin: Decimal | None       # 销售净利率
    grossprofit_margin: Decimal | None     # 销售毛利率
    cogs_of_sales: Decimal | None          # 销售成本率
    expense_of_sales: Decimal | None       # 销售期间费用率
    profit_to_gr: Decimal | None           # 净利润/营业总收入
    saleexp_to_gr: Decimal | None          # 销售费用/营业总收入
    adminexp_to_gr: Decimal | None         # 管理费用/营业总收入
    finaexp_to_gr: Decimal | None          # 财务费用/营业总收入
    impai_ttm: Decimal | None              # 资产减值损失/营业总收入
    gc_of_gr: Decimal | None               # 营业总成本/营业总收入
    op_of_gr: Decimal | None               # 营业利润/营业总收入
    ebit_of_gr: Decimal | None             # 息税前利润/营业总收入
    roe: Decimal | None                    # 净资产收益率
    roe_waa: Decimal | None                # 加权平均净资产收益率
    roe_dt: Decimal | None                 # 净资产收益率(扣除非经常损益)
    roa: Decimal | None                    # 总资产报酬率
    npta: Decimal | None                   # 总资产净利润
    roic: Decimal | None                   # 投入资本回报率
    roe_yearly: Decimal | None             # 年化净资产收益率
    roa2_yearly: Decimal | None            # 年化总资产报酬率
    debt_to_assets: Decimal | None         # 资产负债率
    assets_to_eqt: Decimal | None          # 权益乘数
    dp_assets_to_eqt: Decimal | None       # 权益乘数(杜邦分析)
    ca_to_assets: Decimal | None           # 流动资产/总资产
    nca_to_assets: Decimal | None          # 非流动资产/总资产
    tbassets_to_totalassets: Decimal | None # 有形资产/总资产
    int_to_talcap: Decimal | None          # 带息债务/全部投入资本
    eqt_to_talcap: Decimal | None          # 归属于母公司的股东权益/全部投入资本
    currentdebt_to_debt: Decimal | None    # 流动负债/负债合计
    longdeb_to_debt: Decimal | None        # 非流动负债/负债合计
    ocf_to_shortdebt: Decimal | None       # 经营活动产生的现金流量净额/流动负债
    ocf_to_interestdebt: Decimal | None    # 经营活动产生的现金流量净额/带息债务
    ocf_to_debt: Decimal | None            # 经营活动产生的现金流量净额/负债合计
    cash_to_liqdebt: Decimal | None        # 现金比率
    cash_to_liqdebt_withinterest: Decimal | None  # 现金比率（带息负债）
    op_to_liqdebt: Decimal | None          # 营业利润/流动负债
    op_to_debt: Decimal | None             # 营业利润/负债合计
    roic_yearly: Decimal | None            # 年化投入资本回报率
    profit_to_op: Decimal | None           # 利润总额/营业收入
    q_opincome: Decimal | None             # 经营活动单季度净收益
    q_investincome: Decimal | None         # 价值变动单季度净收益
    q_dtprofit: Decimal | None             # 扣除非经常损益后的单季度净利润
    q_eps: Decimal | None                  # 每股收益(单季度)
    q_netprofit_margin: Decimal | None     # 销售净利率(单季度)
    q_gsprofit_margin: Decimal | None      # 销售毛利率(单季度)
    q_exp_to_sales: Decimal | None         # 销售期间费用率(单季度)
    q_profit_to_gr: Decimal | None         # 净利润/营业总收入(单季度)
    q_saleexp_to_gr: Decimal | None        # 销售费用/营业总收入(单季度)
    q_adminexp_to_gr: Decimal | None       # 管理费用/营业总收入(单季度)
    q_finaexp_to_gr: Decimal | None        # 财务费用/营业总收入(单季度)
    q_impai_to_gr_ttm: Decimal | None      # 资产减值损失/营业总收入(单季度)
    q_gc_to_gr: Decimal | None             # 营业总成本/营业总收入(单季度)
    q_op_to_gr: Decimal | None             # 营业利润/营业总收入(单季度)
    q_roe: Decimal | None                  # 净资产收益率(单季度)
    q_dt_roe: Decimal | None               # 净资产收益率(扣除-单季度)
    q_npta: Decimal | None                 # 总资产净利润(单季度)
    q_opincome_to_ebt: Decimal | None      # 经营活动净收益/利润总额(单季度)
    q_investincome_to_ebt: Decimal | None  # 价值变动净收益/利润总额(单季度)
    q_dtprofit_to_profit: Decimal | None   # 扣除非经常损益后的净利润/净利润(单季度)
    q_salescash_to_or: Decimal | None      # 销售商品提供劳务收到的现金/营业收入(单季度)
    q_ocf_to_sales: Decimal | None         # 经营活动产生的现金流量净额/营业收入(单季度)
    q_ocf_to_or: Decimal | None            # 经营活动产生的现金流量净额/经营活动净收益(单季度)
    update_flag: str | None                # 更新标识（0-未修正，1-已修正）
```

> [!NOTE]
> 以上字段列表基于 Tushare `fina_indicator` 接口的完整输出参数。所有数值型字段使用 `Decimal | None` 以保证精度，因 Tushare 返回的财务指标存在大量 `None` 值。

### Database Model: `FinancialIndicatorModel`

- 表名: `financial_indicator`
- 唯一约束: `UNIQUE(source, third_code, end_date)`
- 索引: `source` + `third_code` (联合索引), `end_date`, `ann_date`
- 审计字段: `created_at`, `updated_at`, `version`（乐观锁）
- 所有财务指标字段为 `Numeric(24, 4)` / `Numeric(24, 6)`, `nullable=True`

### Gateway Interface: `FinancialIndicatorGateway`

```python
class FinancialIndicatorGateway(ABC):
    """从外部数据源拉取财务指标数据（标准接口，仅支持按 ts_code 查询）。"""

    @abstractmethod
    async def fetch_by_stock(
        self, ts_code: str, start_date: date | None = None
    ) -> list[FinancialIndicator]:
        """获取单只股票的财务指标。

        Args:
            ts_code: 股票代码。
            start_date: 可选，报告期起始日期（用于增量同步时只拉取新数据）。
                        为 None 时拉取全部历史。

        内部处理检测式分页（每次 ≤100 条）。
        """
```

### Repository Interface: `FinancialIndicatorRepository`

```python
class FinancialIndicatorRepository(ABC):
    """以 (source, third_code, end_date) 为唯一键批量 upsert。"""

    @abstractmethod
    async def upsert_many(self, records: list[FinancialIndicator]) -> None:
        """批量 upsert。不 commit，由调用方 UnitOfWork 管理。"""

    @abstractmethod
    async def get_latest_end_date(
        self, source: DataSource, third_code: str
    ) -> date | None:
        """查询某只股票本地已有的最新报告期截止日期，用于增量同步断点续传。无记录返回 None。"""
```

## Key Implementation Details

### TokenBucket 复用

`TuShareFinanceIndicatorGateway` 应共享现有的 `TokenBucket` 限流器模式（200次/分钟），与 `TuShareStockDailyGateway` 保持完全一致的限流行为。每个 Gateway 实例独立持有自己的 `TokenBucket`。

### 分页策略：检测式分页

```
function fetch_by_stock(ts_code):
    all_records = []
    end_date_cursor = None  # 初始不设上限

    loop:
        data = api.fina_indicator(ts_code=ts_code, end_date=end_date_cursor)
        all_records.extend(data)

        if len(data) < 100:
            break  # 已获取全部数据

        # 以返回结果中最早的 end_date 前一天作为新的 end_date
        earliest = min(row.end_date for row in data)
        end_date_cursor = earliest - 1 day

        # 防止无限循环
        if end_date_cursor <= 1990-01-01:
            break

    return deduplicate(all_records, key=(ts_code, end_date))
```

### 全量同步 Handler 核心逻辑

```
function handle(SyncFinanceIndicatorFull):
    stocks = basic_repo.find_all_listed(DataSource.TUSHARE)
    synced_set = set()  # 内存防重

    for stock in stocks:
        if stock.third_code in synced_set:
            continue
        try:
            records = gateway.fetch_by_stock(stock.third_code)  # 拉全部历史
            with uow:
                repo.upsert_many(records)
                uow.commit()
            synced_set.add(stock.third_code)
            log.info("同步成功", third_code=stock.third_code, count=len(records))
        except Exception as e:
            log.error("同步失败", third_code=stock.third_code, error=str(e))
            failure_count += 1
            # 不中断，继续下一只
```

### 增量同步 Handler 核心逻辑

```
function handle(SyncFinanceIndicatorIncrement):
    stocks = basic_repo.find_all_listed(DataSource.TUSHARE)
    synced_set = set()

    for stock in stocks:
        if stock.third_code in synced_set:
            continue
        try:
            with uow:
                latest = repo.get_latest_end_date(DataSource.TUSHARE, stock.third_code)

            # 有数据: 从最新报告期的下一天开始;
            # 无数据: start_date=None 拉全部历史 (降级为全量)
            start = latest + 1 day if latest else None

            records = gateway.fetch_by_stock(stock.third_code, start_date=start)

            if records:
                with uow:
                    repo.upsert_many(records)
                    uow.commit()

            synced_set.add(stock.third_code)
            log.info("增量同步", third_code=stock.third_code, count=len(records),
                     start_date=start)
        except Exception as e:
            log.error("增量同步失败", third_code=stock.third_code, error=str(e))
            failure_count += 1
```

## Risks / Trade-offs

| 风险 | 影响 | 缓解措施 |
|:---|:---|:---|
| 进程重启导致进度丢失 | 全量同步需从零重跑（~30分钟） | Upsert 保证幂等，不会产生脏数据 |
| fina_indicator 单次100条限制 | 上市30年以上的公司可能需要多次请求 | 检测式分页 + 去重机制 |
| 增量同步需遍历全市场 | 5000+ 只股票即使无新数据也需逐只查询（~25分钟） | 已完成全量同步后大部分查询返回 0 条或 1-4 条，API 调用量不会倍增；后续可考虑并行度优化 |
| 财报修正导致数据覆盖 | 增量同步基于 `end_date` 推进，已同步的报告期如果被修正，修正后的数据不会被自动拉取 | 定期执行全量同步覆盖，或手动触发单股票同步修复 |
| 频控竞争 | 多条同步流并行时可能互相竞争 token | 各 Gateway 实例独立 `TokenBucket`，同一进程多个并发同步应避免 |
