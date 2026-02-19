# DDD + FastAPI 最佳实践

本文档是项目架构的参考手册，定义了每一层的编码规则和常见模式。

---

## 1. 分层架构

### 依赖规则

```
interfaces → application → domain ← infrastructure
```

**铁律：内层永远不依赖外层。** Domain 层不知道数据库、Web 框架、ORM 的存在。

### 各层职责

| 层 | 职责 | 允许依赖 | 禁止依赖 |
|---|------|---------|---------|
| Domain | 业务规则、实体、值对象、聚合根、仓储接口、领域事件 | 无（纯 Python） | SQLAlchemy, FastAPI, Pydantic |
| Application | 用例编排、命令/查询分发、事务控制 | Domain | SQLAlchemy, FastAPI |
| Infrastructure | ORM 模型、仓储实现、数据库连接、外部服务适配 | Domain | FastAPI |
| Interfaces | HTTP 路由、请求/响应 DTO、中间件、异常映射 | Application, Infrastructure | 直接操作 Domain 实体 |

---

## 2. Domain 层

### 2.1 Entity（实体）

通过 ID 标识，两个实体 ID 相同则视为相等：

```python
@dataclass(eq=False)
class User(Entity[UUID]):
    email: str
    name: str
```

**要点：**
- `eq=False` 关闭 dataclass 默认的值比较，使用基类的 ID 比较
- 实体可变（可以修改属性）
- 所有业务规则都在实体方法中实现

### 2.2 Value Object（值对象）

通过属性值标识，不可变，自我验证：

```python
@dataclass(frozen=True)
class Email(ValueObject):
    address: str

    def _validate(self) -> None:
        if "@" not in self.address:
            raise ValidationException(f"Invalid email: {self.address}")
```

**要点：**
- `frozen=True` 保证不可变
- 在 `_validate()` 中实现不变量验证，创建时自动调用
- 如果两个值对象所有属性都相等，则它们相等

### 2.3 Aggregate Root（聚合根）

聚合根是外部访问的唯一入口，维护一致性边界，收集领域事件：

```python
@dataclass(eq=False)
class Order(AggregateRoot[UUID]):
    customer_id: UUID
    items: list[OrderItem] = field(default_factory=list)
    status: OrderStatus = OrderStatus.DRAFT

    @classmethod
    def create(cls, customer_id: UUID) -> "Order":
        order = cls(id=uuid4(), customer_id=customer_id)
        order.add_event(OrderCreated(order_id=order.id))
        return order

    def add_item(self, product_id: UUID, quantity: int, price: Decimal) -> None:
        if self.status != OrderStatus.DRAFT:
            raise DomainException("Cannot modify a submitted order")
        item = OrderItem(product_id=product_id, quantity=quantity, price=price)
        self.items.append(item)
        self.add_event(ItemAdded(order_id=self.id, product_id=product_id))
```

**要点：**
- 使用工厂方法 `create()` 替代直接构造（方便发布创建事件）
- 所有修改都通过聚合根的方法进行
- 一个事务只修改一个聚合根
- 通过 `add_event()` 收集事件，UoW commit 后统一处理

### 2.4 Domain Event（领域事件）

不可变的值对象，记录"领域中发生了什么"：

```python
@dataclass(frozen=True)
class OrderCreated(DomainEvent):
    order_id: UUID
```

**要点：**
- 用过去时命名（OrderCreated, ItemAdded, PaymentReceived）
- 只携带必要的标识信息，不携带完整实体
- 事件由聚合根产生，在事务提交后发布

### 2.5 Repository（仓储接口）

定义在 Domain 层，是访问聚合根持久化存储的抽象：

```python
class OrderRepository(Repository[Order, UUID]):
    @abstractmethod
    async def find_by_id(self, id: UUID) -> Order | None: ...

    @abstractmethod
    async def save(self, aggregate: Order) -> None: ...

    @abstractmethod
    async def delete(self, aggregate: Order) -> None: ...
```

**要点：**
- 只定义接口，不含实现（实现在 Infrastructure 层）
- 一个聚合根对应一个仓储
- 仓储操作的是聚合根，不是数据库行

---

## 3. Application 层

### 3.1 CQRS: Command vs Query

| | Command | Query |
|---|---------|-------|
| 目的 | 改变状态 | 读取数据 |
| 返回值 | ID / void | 数据 DTO |
| 副作用 | 有（写库、发事件） | 无 |
| 事务 | 需要 UoW | 通常只读 |

```python
@dataclass(frozen=True)
class CreateOrder(Command):
    customer_id: UUID

@dataclass(frozen=True)
class GetOrder(Query):
    order_id: UUID
```

### 3.2 Handler

一个 Command/Query 对应一个 Handler。Handler 编排用例，但不包含业务规则：

```python
class CreateOrderHandler(CommandHandler[CreateOrder, UUID]):
    def __init__(self, repository: OrderRepository) -> None:
        self._repository = repository

    async def handle(self, command: CreateOrder) -> UUID:
        order = Order.create(customer_id=command.customer_id)
        await self._repository.save(order)
        return order.id
```

**要点：**
- Handler 接收抽象接口（仓储），不直接依赖 SQLAlchemy
- Handler 不调用 `commit()`，由 UoW 在外层控制
- Handler 可以调用多个仓储，但建议一个事务只涉及一个聚合

### 3.3 Unit of Work

管理事务边界，确保一组操作要么全成功、要么全回滚：

```python
async with uow:
    order = Order.create(customer_id=cmd.customer_id)
    await order_repo.save(order)
    await uow.commit()  # 统一提交
```

**要点：**
- UoW 在 Application 层定义抽象，Infrastructure 层提供实现
- Repository 的 `save()` 只是把变更挂到 session 上，不 commit
- 异常时 `__aexit__` 自动 rollback

### 3.4 Mediator

串联 Command/Query → Handler 的分发器：

```python
# 接口层使用
note_id = await mediator.send(CreateNote(title="Hello", content="World"))
note = await mediator.query(GetNote(note_id=note_id))
```

**要点：**
- Handler 通过 factory 函数注册（支持依赖注入）
- Mediator 在 lifespan 中创建并挂载到 `app.state`
- 接口层通过 `Depends(get_mediator)` 获取

---

## 4. Infrastructure 层

### 4.1 SQLAlchemy Model

ORM 模型与领域实体分离，放在 `infrastructure/models/`：

```python
class OrderModel(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
```

**要点：**
- 使用 SQLAlchemy 2.0 的 `Mapped` 类型标注
- Model 是数据库关心的结构，Entity 是业务关心的结构，两者独立
- 在 `migrations/env.py` 中 import model 以便 Alembic 自动发现

### 4.2 Repository 实现

继承 `SqlAlchemyRepository` + 具体仓储接口，实现 entity ↔ model 转换：

```python
class SqlAlchemyOrderRepository(SqlAlchemyRepository[Order, UUID], OrderRepository):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, OrderModel)

    def _to_entity(self, model: Any) -> Order:
        return Order(id=model.id, customer_id=model.customer_id, status=model.status)

    def _to_model(self, entity: Order) -> Any:
        return OrderModel(id=entity.id, customer_id=entity.customer_id, status=entity.status.value)
```

---

## 5. Interfaces 层

### 5.1 Router

```python
router = APIRouter(prefix="/orders", tags=["orders"])

@router.post("", response_model=ApiResponse[dict])
async def create_order(
    body: CreateOrderRequest,
    mediator: Mediator = Depends(get_mediator),
    uow: SqlAlchemyUnitOfWork = Depends(get_uow),
) -> ApiResponse[dict]:
    order_id = await mediator.send(CreateOrder(customer_id=body.customer_id))
    await uow.commit()
    return ApiResponse.success(data={"id": str(order_id)})
```

### 5.2 请求/响应模型

请求和响应用 Pydantic BaseModel，放在 `interfaces/api/requests/` 和 `responses/`：

```python
class CreateOrderRequest(BaseModel):
    customer_id: UUID

class OrderResponse(BaseModel):
    id: UUID
    customer_id: UUID
    status: str
```

**要点：**
- Pydantic 模型 ≠ 领域实体。不要把 Entity 直接返回给前端。
- 统一用 `ApiResponse` 包装。

---

## 6. 常见反模式

| 反模式 | 问题 | 正确做法 |
|--------|------|---------|
| 在 Router 里写业务逻辑 | 耦合、不可测 | 业务规则放 Domain，编排放 Handler |
| Repository 里 commit | 破坏事务边界 | 由 UoW 统一 commit |
| Domain 层 import SQLAlchemy | 架构腐化 | Domain 只用纯 Python |
| 一个文件多个不相关的类 | 违反 SRP | 一文件一概念 |
| 跨聚合的事务 | 一致性风险 | 用领域事件实现最终一致 |
| Entity 直接返回给前端 | 泄露内部结构 | 用 Response DTO 映射 |
| 在 Handler 里 new Repository | 不可测 | 构造函数注入 |
| 测试依赖真实数据库 | 慢、不稳定 | 单元测试用 Mock，集成测试用内存 DB |

---

## 7. 新模块开发速查

1. **定义领域模型** — `domain/` 下创建聚合根、事件、仓储接口
2. **写领域单元测试** — `tests/unit/modules/<name>/domain/` 验证领域行为
3. **写 Command/Query + Handler** — `application/` 下编排用例
4. **写 Handler 单元测试** — `tests/unit/modules/<name>/application/`，mock 仓储验证编排逻辑
5. **写 Infrastructure** — `infrastructure/` 实现 ORM Model + Repository
6. **写 API 层** — `interfaces/api/` 定义 Router + 请求/响应模型
7. **注册** — `main.py` 中注册 handler + 挂载 router
8. **创建迁移** — `make migrate-create msg="add xxx table"`
9. **写集成测试** — `tests/integration/` 验证完整流程
