# Tushare 股票财务指标同步 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 从 Tushare `fina_indicator` 接口获取 A 股财务指标数据，支持全市场全量同步、单股票同步、增量同步（逐股断点续传）。

**Architecture:** DDD + 整洁架构。Domain → Infrastructure → Application → Interface 单向依赖。唯一键 `(source, third_code, end_date)`，upsert 策略，TokenBucket 限流（200次/分钟），检测式分页（返回 ≥100 行则继续翻页）。

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy async + asyncpg, PostgreSQL, pytest

> **字段完整列表：** 见 `design.md` `Data Structures` 章节，共 ~100 个 `Decimal | None` 字段。

---

### Task 1: 领域实体与接口定义

**Files:**
- `src/app/modules/data_engineering/domain/entities/financial_indicator.py`
- `src/app/modules/data_engineering/domain/gateways/financial_indicator_gateway.py`
- `src/app/modules/data_engineering/domain/repositories/financial_indicator_repository.py`
- `tests/unit/modules/data_engineering/domain/test_financial_indicator.py`

**Step 1: 先写测试（失败）**

```bash
pytest tests/unit/modules/data_engineering/domain/test_financial_indicator.py -v
# 预期: ImportError / ModuleNotFoundError
```

**Step 2: 实现 `FinancialIndicator` 实体**

```python
# src/app/modules/data_engineering/domain/entities/financial_indicator.py
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from app.shared_kernel.domain.entity import Entity
from ..value_objects.data_source import DataSource

@dataclass(eq=False)
class FinancialIndicator(Entity[int | None]):
    """财务指标实体。逻辑唯一键：(source, third_code, end_date)。"""
    id: int | None
    source: DataSource
    third_code: str
    ann_date: date | None
    end_date: date
    eps: Decimal | None
    dt_eps: Decimal | None
    total_revenue_ps: Decimal | None
    revenue_ps: Decimal | None
    capital_rese_ps: Decimal | None
    surplus_rese_ps: Decimal | None
    undist_profit_ps: Decimal | None
    extra_item: Decimal | None
    profit_dedt: Decimal | None
    gross_margin: Decimal | None
    current_ratio: Decimal | None
    quick_ratio: Decimal | None
    cash_ratio: Decimal | None
    ar_turn: Decimal | None
    ca_turn: Decimal | None
    fa_turn: Decimal | None
    assets_turn: Decimal | None
    op_income: Decimal | None
    ebit: Decimal | None
    ebitda: Decimal | None
    fcff: Decimal | None
    fcfe: Decimal | None
    current_exint: Decimal | None
    noncurrent_exint: Decimal | None
    interestdebt: Decimal | None
    netdebt: Decimal | None
    tangible_asset: Decimal | None
    working_capital: Decimal | None
    networking_capital: Decimal | None
    invest_capital: Decimal | None
    retained_earnings: Decimal | None
    diluted2_eps: Decimal | None
    bps: Decimal | None
    ocfps: Decimal | None
    retainedps: Decimal | None
    cfps: Decimal | None
    ebit_ps: Decimal | None
    fcff_ps: Decimal | None
    fcfe_ps: Decimal | None
    netprofit_margin: Decimal | None
    grossprofit_margin: Decimal | None
    cogs_of_sales: Decimal | None
    expense_of_sales: Decimal | None
    profit_to_gr: Decimal | None
    saleexp_to_gr: Decimal | None
    adminexp_to_gr: Decimal | None
    finaexp_to_gr: Decimal | None
    impai_ttm: Decimal | None
    gc_of_gr: Decimal | None
    op_of_gr: Decimal | None
    ebit_of_gr: Decimal | None
    roe: Decimal | None
    roe_waa: Decimal | None
    roe_dt: Decimal | None
    roa: Decimal | None
    npta: Decimal | None
    roic: Decimal | None
    roe_yearly: Decimal | None
    roa2_yearly: Decimal | None
    debt_to_assets: Decimal | None
    assets_to_eqt: Decimal | None
    dp_assets_to_eqt: Decimal | None
    ca_to_assets: Decimal | None
    nca_to_assets: Decimal | None
    tbassets_to_totalassets: Decimal | None
    int_to_talcap: Decimal | None
    eqt_to_talcap: Decimal | None
    currentdebt_to_debt: Decimal | None
    longdeb_to_debt: Decimal | None
    ocf_to_shortdebt: Decimal | None
    ocf_to_interestdebt: Decimal | None
    ocf_to_debt: Decimal | None
    cash_to_liqdebt: Decimal | None
    cash_to_liqdebt_withinterest: Decimal | None
    op_to_liqdebt: Decimal | None
    op_to_debt: Decimal | None
    roic_yearly: Decimal | None
    profit_to_op: Decimal | None
    q_opincome: Decimal | None
    q_investincome: Decimal | None
    q_dtprofit: Decimal | None
    q_eps: Decimal | None
    q_netprofit_margin: Decimal | None
    q_gsprofit_margin: Decimal | None
    q_exp_to_sales: Decimal | None
    q_profit_to_gr: Decimal | None
    q_saleexp_to_gr: Decimal | None
    q_adminexp_to_gr: Decimal | None
    q_finaexp_to_gr: Decimal | None
    q_impai_to_gr_ttm: Decimal | None
    q_gc_to_gr: Decimal | None
    q_op_to_gr: Decimal | None
    q_roe: Decimal | None
    q_dt_roe: Decimal | None
    q_npta: Decimal | None
    q_opincome_to_ebt: Decimal | None
    q_investincome_to_ebt: Decimal | None
    q_dtprofit_to_profit: Decimal | None
    q_salescash_to_or: Decimal | None
    q_ocf_to_sales: Decimal | None
    q_ocf_to_or: Decimal | None
    update_flag: str | None
```

**Step 3: 实现抽象接口**

```python
# src/app/modules/data_engineering/domain/gateways/financial_indicator_gateway.py
from abc import ABC, abstractmethod
from datetime import date
from ..entities.financial_indicator import FinancialIndicator

class FinancialIndicatorGateway(ABC):
    @abstractmethod
    async def fetch_by_stock(
        self, ts_code: str, start_date: date | None = None
    ) -> list[FinancialIndicator]:
        """拉取单只股票所有历史财务指标（含检测式分页）。"""
        ...
```

```python
# src/app/modules/data_engineering/domain/repositories/financial_indicator_repository.py
from abc import ABC, abstractmethod
from datetime import date
from ..entities.financial_indicator import FinancialIndicator
from ..value_objects.data_source import DataSource

class FinancialIndicatorRepository(ABC):
    @abstractmethod
    async def upsert_many(self, records: list[FinancialIndicator]) -> None:
        """批量 upsert，不 commit，由 UnitOfWork 管理。"""
        ...

    @abstractmethod
    async def get_latest_end_date(self, source: DataSource, third_code: str) -> date | None:
        """查最新报告期截止日，无记录返回 None。"""
        ...
```

**Step 4: 实现单元测试**

```python
# tests/unit/modules/data_engineering/domain/test_financial_indicator.py
from dataclasses import fields
from datetime import date
from decimal import Decimal
from app.modules.data_engineering.domain.entities.financial_indicator import FinancialIndicator
from app.modules.data_engineering.domain.value_objects.data_source import DataSource

_FIXED = {"id", "source", "third_code", "end_date"}

def _make(**kwargs) -> FinancialIndicator:
    base = {
        "id": None, "source": DataSource.TUSHARE,
        "third_code": "000001.SZ", "end_date": date(2023, 12, 31),
        **{f.name: None for f in fields(FinancialIndicator) if f.name not in _FIXED},
    }
    base.update(kwargs)
    return FinancialIndicator(**base)

def test_identity_by_id():
    assert _make(id=1) == _make(id=1)

def test_none_id_not_equal():
    assert _make(id=None) != _make(id=None)

def test_all_numeric_fields_accept_none():
    ind = _make(eps=None, roe=None, ann_date=None)
    assert ind.eps is None and ind.roe is None and ind.ann_date is None

def test_unique_key_fields():
    ind = _make(source=DataSource.TUSHARE, third_code="600000.SH", end_date=date(2023, 9, 30))
    assert (ind.source, ind.third_code, ind.end_date) == (
        DataSource.TUSHARE, "600000.SH", date(2023, 9, 30)
    )

def test_eps_decimal_precision():
    assert _make(eps=Decimal("1.2345")).eps == Decimal("1.2345")
```

**Step 5: 再次运行测试确认通过**

```bash
pytest tests/unit/modules/data_engineering/domain/test_financial_indicator.py -v
# 预期: 5 passed
```

**Step 6: Commit**

```bash
git add src/app/modules/data_engineering/domain/entities/financial_indicator.py \
        src/app/modules/data_engineering/domain/gateways/financial_indicator_gateway.py \
        src/app/modules/data_engineering/domain/repositories/financial_indicator_repository.py \
        tests/unit/modules/data_engineering/domain/test_financial_indicator.py
git commit -m "feat(data_engineering): add FinancialIndicator entity and domain interfaces"
```

---

### Task 2: SQLAlchemy 模型与数据库迁移

**Files:**
- `src/app/modules/data_engineering/infrastructure/models/financial_indicator_model.py`
- `migrations/versions/YYYYMMDD_HHMM_add_financial_indicator_table.py`

**Step 1: 实现 ORM 模型**

字段规则（与实体对应，全部 `nullable=True`）：
- **每股/比率类字段** → `Numeric(24, 4)`（大多数字段）
- **大金额类字段**（`profit_dedt`, `gross_margin`, `op_income`, `ebit`, `ebitda`, `fcff`, `fcfe`, `*_exint`, `interestdebt`, `netdebt`, `tangible_asset`, `working_capital`, `networking_capital`, `invest_capital`, `retained_earnings`, `q_opincome`, `q_investincome`, `q_dtprofit`）→ `Numeric(24, 6)`

```python
# src/app/modules/data_engineering/infrastructure/models/financial_indicator_model.py
from datetime import date, datetime
from sqlalchemy import Date, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.shared_kernel.infrastructure.database import Base

class FinancialIndicatorModel(Base):
    __tablename__ = "financial_indicator"
    __table_args__ = (
        UniqueConstraint("source", "third_code", "end_date", name="uq_financial_indicator_key"),
    )
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    third_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    ann_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    # 每股/比率类（Numeric(24,4)），大金额类（Numeric(24,6)）
    # 按实体字段顺序逐一声明，规则见上方字段规则说明
    eps: Mapped[float | None] = mapped_column(Numeric(24, 4), nullable=True)
    # ... 按 FinancialIndicator 实体字段顺序逐一添加，规则同上
    update_flag: Mapped[str | None] = mapped_column(String(4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now(), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        default=func.now(), server_default=func.now(), onupdate=func.now()
    )
```

**Step 2: 注册模型并生成迁移**

在 `migrations/env.py` 中 import `FinancialIndicatorModel`，然后：

```bash
alembic revision --autogenerate -m "add financial indicator table"
# 检查生成的迁移文件，确认表结构和唯一约束正确
alembic upgrade head
```

**Step 3: Commit**

```bash
git add src/app/modules/data_engineering/infrastructure/models/financial_indicator_model.py \
        migrations/versions/
git commit -m "feat(data_engineering): add financial_indicator SQLAlchemy model and migration"
```

---

### Task 3: Repository 实现（TDD）

**Files:**
- `src/app/modules/data_engineering/infrastructure/repositories/mappers/financial_indicator_persistence_mapper.py`
- `src/app/modules/data_engineering/infrastructure/repositories/sqlalchemy_financial_indicator_repository.py`
- `tests/integration/modules/data_engineering/infrastructure/test_sqlalchemy_financial_indicator_repository.py`

**Step 1: 先写集成测试（失败）**

```python
# tests/integration/modules/data_engineering/infrastructure/test_sqlalchemy_financial_indicator_repository.py
import pytest
from datetime import date
from decimal import Decimal
from dataclasses import fields as dc_fields
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.data_engineering.domain.entities.financial_indicator import FinancialIndicator
from app.modules.data_engineering.domain.value_objects.data_source import DataSource
from app.modules.data_engineering.infrastructure.repositories.sqlalchemy_financial_indicator_repository import (
    SqlAlchemyFinancialIndicatorRepository,
)

_FIXED = {"id", "source", "third_code", "end_date"}

def _make(third_code="000001.SZ", end_date=date(2023, 12, 31), **kwargs) -> FinancialIndicator:
    base = {
        "id": None, "source": DataSource.TUSHARE,
        "third_code": third_code, "end_date": end_date,
        **{f.name: None for f in dc_fields(FinancialIndicator) if f.name not in _FIXED},
    }
    base.update(kwargs)
    return FinancialIndicator(**base)

@pytest.mark.asyncio
async def test_upsert_many_and_get_latest_end_date(db_session: AsyncSession):
    repo = SqlAlchemyFinancialIndicatorRepository(db_session)
    records = [
        _make(end_date=date(2023, 3, 31), eps=Decimal("1.0")),
        _make(end_date=date(2023, 12, 31), eps=Decimal("2.0")),
    ]
    await repo.upsert_many(records)
    await db_session.commit()

    latest = await repo.get_latest_end_date(DataSource.TUSHARE, "000001.SZ")
    assert latest == date(2023, 12, 31)

@pytest.mark.asyncio
async def test_upsert_many_is_idempotent(db_session: AsyncSession):
    repo = SqlAlchemyFinancialIndicatorRepository(db_session)
    record = _make(end_date=date(2023, 12, 31), eps=Decimal("1.0"))
    await repo.upsert_many([record])
    await db_session.commit()
    updated = _make(end_date=date(2023, 12, 31), eps=Decimal("9.9"))
    await repo.upsert_many([updated])
    await db_session.commit()

    latest = await repo.get_latest_end_date(DataSource.TUSHARE, "000001.SZ")
    assert latest == date(2023, 12, 31)  # 只有1条记录

@pytest.mark.asyncio
async def test_get_latest_end_date_no_records(db_session: AsyncSession):
    repo = SqlAlchemyFinancialIndicatorRepository(db_session)
    result = await repo.get_latest_end_date(DataSource.TUSHARE, "999999.SZ")
    assert result is None
```

```bash
pytest tests/integration/modules/data_engineering/infrastructure/test_sqlalchemy_financial_indicator_repository.py -v
# 预期: ImportError
```

**Step 2: 实现 Persistence Mapper**

```python
# src/app/modules/data_engineering/infrastructure/repositories/mappers/financial_indicator_persistence_mapper.py
from dataclasses import fields as dc_fields, asdict
from app.modules.data_engineering.domain.entities.financial_indicator import FinancialIndicator
from app.modules.data_engineering.domain.value_objects.data_source import DataSource
from app.modules.data_engineering.infrastructure.models.financial_indicator_model import FinancialIndicatorModel

_SKIP = {"id"}
_NUMERIC_FIELDS = {
    f.name for f in dc_fields(FinancialIndicator)
    if f.name not in {"id", "source", "third_code", "ann_date", "end_date", "update_flag"}
}

class FinancialIndicatorPersistenceMapper:
    @staticmethod
    def to_dict(entity: FinancialIndicator) -> dict:
        d = asdict(entity)
        d["source"] = entity.source.value
        d.pop("id", None)
        return d

    @staticmethod
    def to_entity(model: FinancialIndicatorModel) -> FinancialIndicator:
        from decimal import Decimal
        kwargs = {
            f.name: (Decimal(str(getattr(model, f.name)))
                     if f.name in _NUMERIC_FIELDS and getattr(model, f.name) is not None
                     else getattr(model, f.name))
            for f in dc_fields(FinancialIndicator) if f.name != "source"
        }
        kwargs["id"] = model.id
        kwargs["source"] = DataSource(model.source)
        return FinancialIndicator(**kwargs)
```

**Step 3: 实现 Repository**

```python
# src/app/modules/data_engineering/infrastructure/repositories/sqlalchemy_financial_indicator_repository.py
from datetime import date
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.data_engineering.domain.entities.financial_indicator import FinancialIndicator
from app.modules.data_engineering.domain.repositories.financial_indicator_repository import FinancialIndicatorRepository
from app.modules.data_engineering.domain.value_objects.data_source import DataSource
from app.modules.data_engineering.infrastructure.models.financial_indicator_model import FinancialIndicatorModel
from app.modules.data_engineering.infrastructure.repositories.mappers.financial_indicator_persistence_mapper import FinancialIndicatorPersistenceMapper

CONFLICT_COLS = ["source", "third_code", "end_date"]
BATCH_SIZE = 50  # ~100 cols × 50 rows = 5000 params，低于 asyncpg 32767 上限

class SqlAlchemyFinancialIndicatorRepository(FinancialIndicatorRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_many(self, records: list[FinancialIndicator]) -> None:
        if not records:
            return
        mapper = FinancialIndicatorPersistenceMapper
        rows = [mapper.to_dict(r) for r in records]
        dialect = self._session.bind.dialect.name if self._session.bind else "postgresql"
        insert_fn = pg_insert if dialect == "postgresql" else sqlite_insert
        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i : i + BATCH_SIZE]
            update_cols = {k: v for k, v in batch[0].items() if k not in CONFLICT_COLS}
            stmt = (
                insert_fn(FinancialIndicatorModel)
                .values(batch)
                .on_conflict_do_update(index_elements=CONFLICT_COLS, set_=update_cols)
            )
            await self._session.execute(stmt)

    async def get_latest_end_date(self, source: DataSource, third_code: str) -> date | None:
        stmt = select(func.max(FinancialIndicatorModel.end_date)).where(
            FinancialIndicatorModel.source == source.value,
            FinancialIndicatorModel.third_code == third_code,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
```

**Step 4: 运行测试确认通过**

```bash
pytest tests/integration/modules/data_engineering/infrastructure/test_sqlalchemy_financial_indicator_repository.py -v
# 预期: 3 passed
```

**Step 5: Commit**

```bash
git add src/app/modules/data_engineering/infrastructure/repositories/mappers/financial_indicator_persistence_mapper.py \
        src/app/modules/data_engineering/infrastructure/repositories/sqlalchemy_financial_indicator_repository.py \
        tests/integration/modules/data_engineering/infrastructure/test_sqlalchemy_financial_indicator_repository.py
git commit -m "feat(data_engineering): add FinancialIndicator repository with upsert"
```

---

### Task 4: Tushare Gateway + Mapper（TDD）

**Files:**
- `src/app/modules/data_engineering/infrastructure/gateways/mappers/tushare_finance_indicator_mapper.py`
- `src/app/modules/data_engineering/infrastructure/gateways/tushare_finance_indicator_gateway.py`
- `tests/unit/modules/data_engineering/infrastructure/gateways/test_tushare_finance_indicator_gateway.py`

**Step 1: 先写单元测试（失败）**

```python
# tests/unit/.../test_tushare_finance_indicator_gateway.py
import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock
from app.modules.data_engineering.infrastructure.gateways.tushare_finance_indicator_gateway import TuShareFinanceIndicatorGateway

def _row(**kw):
    """构造最小 API 行，所有财务字段默认 None，ts_code/end_date 必填。"""
    defaults = {"ts_code": "000001.SZ", "ann_date": "20240330", "end_date": "20231231",
                "eps": "1.23", "update_flag": None}
    # 其余 ~95 个财务字段均 None，实现时用 dataclasses.fields 遍历补全
    defaults.update(kw)
    return defaults

@pytest.mark.asyncio
async def test_fetch_single_page():
    mock_pro = MagicMock()
    mock_pro.fina_indicator.return_value = MagicMock(to_dict=MagicMock(return_value=[_row()]))
    gw = TuShareFinanceIndicatorGateway(pro=mock_pro)
    results = await gw.fetch_by_stock("000001.SZ")
    assert len(results) == 1 and results[0].eps == Decimal("1.23")

@pytest.mark.asyncio
async def test_fetch_with_start_date():
    mock_pro = MagicMock()
    mock_pro.fina_indicator.return_value = MagicMock(to_dict=MagicMock(return_value=[]))
    gw = TuShareFinanceIndicatorGateway(pro=mock_pro)
    await gw.fetch_by_stock("000001.SZ", start_date=date(2023, 1, 1))
    assert mock_pro.fina_indicator.call_args.kwargs.get("start_date") == "20230101"

@pytest.mark.asyncio
async def test_pagination_stops_when_less_than_100():
    mock_pro = MagicMock()
    mock_pro.fina_indicator.return_value = MagicMock(to_dict=MagicMock(return_value=[_row()] * 50))
    gw = TuShareFinanceIndicatorGateway(pro=mock_pro)
    results = await gw.fetch_by_stock("000001.SZ")
    assert mock_pro.fina_indicator.call_count == 1 and len(results) == 50
```

**Step 2: 实现 Mapper**

```python
# tushare_finance_indicator_mapper.py
from dataclasses import fields as dc_fields
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from app.modules.data_engineering.domain.entities.financial_indicator import FinancialIndicator
from app.modules.data_engineering.domain.value_objects.data_source import DataSource

_DATE_FIELDS = {"ann_date", "end_date"}
_STR_FIELDS = {"update_flag"}

def _d(val) -> Decimal | None:
    if val is None or val == "": return None
    try: return Decimal(str(val))
    except InvalidOperation: return None

def _dt(val) -> date | None:
    return datetime.strptime(val, "%Y%m%d").date() if val else None

class TuShareFinanceIndicatorMapper:
    @staticmethod
    def to_entity(row: dict) -> FinancialIndicator:
        kwargs = {"id": None, "source": DataSource.TUSHARE, "third_code": row["ts_code"]}
        for f in dc_fields(FinancialIndicator):
            if f.name in {"id", "source", "third_code"}: continue
            v = row.get(f.name)
            kwargs[f.name] = _dt(v) if f.name in _DATE_FIELDS else (v if f.name in _STR_FIELDS else _d(v))
        return FinancialIndicator(**kwargs)
```

**Step 3: 实现 Gateway（TokenBucket + 检测式分页）**

```python
# tushare_finance_indicator_gateway.py
import asyncio, logging
from datetime import date
from app.modules.data_engineering.domain.gateways.financial_indicator_gateway import FinancialIndicatorGateway
from app.modules.data_engineering.infrastructure.gateways.tushare_stock_daily_gateway import TokenBucket
from .mappers.tushare_finance_indicator_mapper import TuShareFinanceIndicatorMapper

logger = logging.getLogger(__name__)
PAGE_SIZE = 100

class TuShareFinanceIndicatorGateway(FinancialIndicatorGateway):
    def __init__(self, pro, rate_limit: int = 200) -> None:
        self._pro = pro
        self._bucket = TokenBucket(rate=rate_limit, capacity=rate_limit)
        self._mapper = TuShareFinanceIndicatorMapper()

    async def fetch_by_stock(self, ts_code: str, start_date: date | None = None):
        results, offset = [], 0
        while True:
            await self._bucket.acquire()
            kw = dict(ts_code=ts_code, limit=PAGE_SIZE, offset=offset)
            if start_date: kw["start_date"] = start_date.strftime("%Y%m%d")
            rows = (await asyncio.to_thread(self._pro.fina_indicator, **kw)).to_dict("records")
            if not rows: break
            results.extend(self._mapper.to_entity(r) for r in rows)
            logger.debug("fina_indicator %s offset=%d got=%d", ts_code, offset, len(rows))
            if len(rows) < PAGE_SIZE: break
            offset += PAGE_SIZE
        return results
```

**Step 4: 运行测试 → Commit**

```bash
pytest tests/unit/modules/data_engineering/infrastructure/gateways/test_tushare_finance_indicator_gateway.py -v
git add src/app/modules/data_engineering/infrastructure/gateways/mappers/tushare_finance_indicator_mapper.py \
        src/app/modules/data_engineering/infrastructure/gateways/tushare_finance_indicator_gateway.py \
        tests/unit/modules/data_engineering/infrastructure/gateways/test_tushare_finance_indicator_gateway.py
git commit -m "feat(data_engineering): add TuShare finance indicator gateway with pagination"
```

---

### Task 5: Commands + Handlers（TDD）

**Files:**
- `src/app/modules/data_engineering/application/commands/sync_finance_indicator_commands.py`
- `src/app/modules/data_engineering/application/commands/sync_finance_indicator_full_handler.py`
- `src/app/modules/data_engineering/application/commands/sync_finance_indicator_by_stock_handler.py`
- `src/app/modules/data_engineering/application/commands/sync_finance_indicator_increment_handler.py`
- `tests/unit/modules/data_engineering/application/test_sync_finance_indicator_handlers.py`

**Step 1: 定义 Commands**

```python
# sync_finance_indicator_commands.py
from dataclasses import dataclass, field

@dataclass
class SyncFinanceIndicatorFull:
    ts_codes: list[str] = field(default_factory=list)  # 空=全市场

@dataclass
class SyncFinanceIndicatorByStock:
    ts_code: str

@dataclass
class SyncFinanceIndicatorIncrement:
    ts_codes: list[str] = field(default_factory=list)

@dataclass
class SyncFinanceIndicatorResult:
    total: int
    success_count: int
    failure_count: int
    synced_records: int
```

**Step 2: 先写单元测试（失败）**

```python
# tests/.../test_sync_finance_indicator_handlers.py
import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock
from app.modules.data_engineering.application.commands.sync_finance_indicator_commands import *
from app.modules.data_engineering.application.commands.sync_finance_indicator_full_handler import SyncFinanceIndicatorFullHandler
from app.modules.data_engineering.application.commands.sync_finance_indicator_by_stock_handler import SyncFinanceIndicatorByStockHandler
from app.modules.data_engineering.application.commands.sync_finance_indicator_increment_handler import SyncFinanceIndicatorIncrementHandler
from app.modules.data_engineering.domain.value_objects.data_source import DataSource

def _uow():
    u = AsyncMock(); u.__aenter__ = AsyncMock(return_value=u); u.__aexit__ = AsyncMock(return_value=False)
    return u

def _stock(code="000001.SZ"):
    s = MagicMock(); s.third_code = code; s.source = DataSource.TUSHARE; return s

@pytest.mark.asyncio
async def test_full_syncs_all_stocks():
    basic_repo = AsyncMock(); basic_repo.find_all_listed.return_value = [_stock()]
    fi_repo = AsyncMock()
    gateway = AsyncMock(); gateway.fetch_by_stock.return_value = [MagicMock()]
    result = await SyncFinanceIndicatorFullHandler(basic_repo, fi_repo, gateway, _uow()).handle(SyncFinanceIndicatorFull())
    assert result.total == 1 and result.success_count == 1 and result.failure_count == 0

@pytest.mark.asyncio
async def test_by_stock_returns_count():
    fi_repo = AsyncMock()
    gateway = AsyncMock(); gateway.fetch_by_stock.return_value = [MagicMock(), MagicMock()]
    result = await SyncFinanceIndicatorByStockHandler(fi_repo, gateway, _uow()).handle(SyncFinanceIndicatorByStock("000001.SZ"))
    assert result.synced_records == 2

@pytest.mark.asyncio
async def test_increment_uses_latest_end_date():
    basic_repo = AsyncMock(); basic_repo.find_all_listed.return_value = [_stock()]
    fi_repo = AsyncMock(); fi_repo.get_latest_end_date.return_value = date(2023, 9, 30)
    gateway = AsyncMock(); gateway.fetch_by_stock.return_value = []
    await SyncFinanceIndicatorIncrementHandler(basic_repo, fi_repo, gateway, _uow()).handle(SyncFinanceIndicatorIncrement())
    gateway.fetch_by_stock.assert_called_once_with("000001.SZ", start_date=date(2023, 10, 1))
```

**Step 3: 实现三个 Handler**

各 Handler 模式与 `SyncStockDailyHistoryHandler` 完全一致：`find_all_listed` → 逐股 `async with uow` → `gateway.fetch_by_stock` → `fi_repo.upsert_many` → `uow.commit()`，异常独立捕获后继续。

- **Full Handler**：调 `gateway.fetch_by_stock(stock.third_code)`（无 start_date）
- **ByStock Handler**：调 `gateway.fetch_by_stock(cmd.ts_code)`，单次事务
- **Increment Handler**：先 `fi_repo.get_latest_end_date` → `start_date = latest + timedelta(days=1)`，再 `gateway.fetch_by_stock(ts_code, start_date=start_date)`

**Step 4: 运行测试 → Commit**

```bash
pytest tests/unit/modules/data_engineering/application/test_sync_finance_indicator_handlers.py -v
git add src/app/modules/data_engineering/application/commands/sync_finance_indicator_*.py \
        tests/unit/modules/data_engineering/application/test_sync_finance_indicator_handlers.py
git commit -m "feat(data_engineering): add finance indicator sync handlers"
```

---

### Task 6: HTTP Router + 依赖注入 + API 集成测试

**Files:**
- `src/app/modules/data_engineering/interfaces/api/finance_indicator_router.py`
- Modify: `src/app/modules/data_engineering/interfaces/dependencies.py`
- `tests/api/modules/data_engineering/interfaces/api/test_finance_indicator_router.py`

**Step 1: 先写集成测试（失败）**

```python
# tests/api/.../test_finance_indicator_router.py
import pytest
from unittest.mock import AsyncMock
from httpx import AsyncClient, ASGITransport
from app.config import create_app
from app.modules.data_engineering.application.commands.sync_finance_indicator_commands import SyncFinanceIndicatorResult
from app.modules.data_engineering.interfaces.dependencies import (
    get_sync_finance_indicator_full_handler,
    get_sync_finance_indicator_by_stock_handler,
    get_sync_finance_indicator_increment_handler,
)

_R = SyncFinanceIndicatorResult(total=10, success_count=9, failure_count=1, synced_records=360)
_RS = SyncFinanceIndicatorResult(total=1, success_count=1, failure_count=0, synced_records=40)

@pytest.fixture
def client_with_mocks():
    app = create_app()
    for dep, ret in [(get_sync_finance_indicator_full_handler, _R),
                     (get_sync_finance_indicator_by_stock_handler, _RS),
                     (get_sync_finance_indicator_increment_handler, _R)]:
        h = AsyncMock(); h.handle.return_value = ret
        app.dependency_overrides[dep] = lambda _h=h: _h
    return app

@pytest.mark.asyncio
async def test_sync_full(client_with_mocks):
    async with AsyncClient(transport=ASGITransport(app=client_with_mocks), base_url="http://test") as c:
        r = await c.post("/api/v1/finance-indicator/sync/full")
    assert r.status_code == 200 and r.json()["success_count"] == 9

@pytest.mark.asyncio
async def test_sync_by_stock(client_with_mocks):
    async with AsyncClient(transport=ASGITransport(app=client_with_mocks), base_url="http://test") as c:
        r = await c.post("/api/v1/finance-indicator/sync/by-stock/000001.SZ")
    assert r.status_code == 200 and r.json()["synced_records"] == 40

@pytest.mark.asyncio
async def test_sync_increment(client_with_mocks):
    async with AsyncClient(transport=ASGITransport(app=client_with_mocks), base_url="http://test") as c:
        r = await c.post("/api/v1/finance-indicator/sync/increment")
    assert r.status_code == 200 and r.json()["total"] == 10
```

**Step 2: 实现 Router**

```python
# finance_indicator_router.py
from fastapi import APIRouter, Depends
from app.modules.data_engineering.application.commands.sync_finance_indicator_commands import (
    SyncFinanceIndicatorFull, SyncFinanceIndicatorByStock, SyncFinanceIndicatorIncrement,
)
from app.modules.data_engineering.interfaces.dependencies import (
    get_sync_finance_indicator_full_handler,
    get_sync_finance_indicator_by_stock_handler,
    get_sync_finance_indicator_increment_handler,
)

router = APIRouter(prefix="/finance-indicator", tags=["finance-indicator"])

@router.post("/sync/full")
async def sync_full(handler=Depends(get_sync_finance_indicator_full_handler)):
    r = await handler.handle(SyncFinanceIndicatorFull())
    return r.__dict__

@router.post("/sync/by-stock/{ts_code}")
async def sync_by_stock(ts_code: str, handler=Depends(get_sync_finance_indicator_by_stock_handler)):
    r = await handler.handle(SyncFinanceIndicatorByStock(ts_code=ts_code))
    return r.__dict__

@router.post("/sync/increment")
async def sync_increment(handler=Depends(get_sync_finance_indicator_increment_handler)):
    r = await handler.handle(SyncFinanceIndicatorIncrement())
    return r.__dict__
```

**Step 3: 更新 `dependencies.py`**

在文件末尾追加三个依赖函数，参照现有 `get_sync_stock_daily_history_handler` 的模式（注入 session/uow/pro）：

```python
# 追加到 dependencies.py 末尾
from app.modules.data_engineering.infrastructure.repositories.sqlalchemy_financial_indicator_repository import SqlAlchemyFinancialIndicatorRepository
from app.modules.data_engineering.infrastructure.gateways.tushare_finance_indicator_gateway import TuShareFinanceIndicatorGateway
from app.modules.data_engineering.application.commands.sync_finance_indicator_full_handler import SyncFinanceIndicatorFullHandler
from app.modules.data_engineering.application.commands.sync_finance_indicator_by_stock_handler import SyncFinanceIndicatorByStockHandler
from app.modules.data_engineering.application.commands.sync_finance_indicator_increment_handler import SyncFinanceIndicatorIncrementHandler

async def get_sync_finance_indicator_full_handler(session=Depends(get_session), uow=Depends(get_uow), pro=Depends(get_tushare_pro)):
    return SyncFinanceIndicatorFullHandler(SqlAlchemyStockBasicRepository(session), SqlAlchemyFinancialIndicatorRepository(session), TuShareFinanceIndicatorGateway(pro=pro), uow)

async def get_sync_finance_indicator_by_stock_handler(session=Depends(get_session), uow=Depends(get_uow), pro=Depends(get_tushare_pro)):
    return SyncFinanceIndicatorByStockHandler(SqlAlchemyFinancialIndicatorRepository(session), TuShareFinanceIndicatorGateway(pro=pro), uow)

async def get_sync_finance_indicator_increment_handler(session=Depends(get_session), uow=Depends(get_uow), pro=Depends(get_tushare_pro)):
    return SyncFinanceIndicatorIncrementHandler(SqlAlchemyStockBasicRepository(session), SqlAlchemyFinancialIndicatorRepository(session), TuShareFinanceIndicatorGateway(pro=pro), uow)
```

**Step 4: 在主 App 注册 Router**

在 `app/config.py`（或 router 注册处）添加：

```python
from app.modules.data_engineering.interfaces.api.finance_indicator_router import router as finance_indicator_router
app.include_router(finance_indicator_router, prefix="/api/v1")
```

**Step 5: 运行全部测试 → Commit**

```bash
pytest tests/api/modules/data_engineering/interfaces/api/test_finance_indicator_router.py -v
pytest tests/ -v --tb=short  # 全量回归
git add src/app/modules/data_engineering/interfaces/api/finance_indicator_router.py \
        src/app/modules/data_engineering/interfaces/dependencies.py \
        tests/api/modules/data_engineering/interfaces/api/test_finance_indicator_router.py
git commit -m "feat(data_engineering): add finance indicator HTTP router and DI wiring"
```

---

### 完成验证

```bash
# 运行全部测试
pytest tests/ -v --tb=short

# 检查架构守护
make lint  # 或 python -m pytest tests/architecture/

# 确认迁移已应用
alembic current
```

**所有测试通过后，该 feature 实现完毕。**

