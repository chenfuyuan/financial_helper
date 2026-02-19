---
description: DDD + 整洁架构编码规则
globs: src/**/*.py
---

# 架构规则

## 分层依赖（只允许向内依赖）

```
interfaces → application → domain ← infrastructure
```

- domain 不 import 任何其他层
- application 只 import domain
- infrastructure import domain（实现接口）
- interfaces import application + infrastructure（组装依赖）

## Domain 层

- 实体: `@dataclass(eq=False)` + 通过 ID 比较
- 值对象: `@dataclass(frozen=True)` + `_validate()` 自校验
- 聚合根: 继承 `AggregateRoot[ID]` + 用 `add_event()` 发布领域事件
- 仓储: 只定义抽象接口，不含实现
- 异常: 继承 `DomainException`

## Application 层

- Command/Query: `@dataclass(frozen=True)` 不可变
- Handler: 一个 Command/Query 对应一个 Handler
- UnitOfWork: 应用层控制事务边界，Repository 不自行 commit
- Mediator: 通过 `mediator.send(command)` / `mediator.query(query)` 分发

## Infrastructure 层

- SqlAlchemy Model: 继承 `Base`，放在 `models/` 目录
- Repository 实现: 继承 `SqlAlchemyRepository` + 具体模块仓储接口
- 必须实现 `_to_entity()` 和 `_to_model()` 转换方法

## Interfaces 层

- Router 使用 `APIRouter`，通过 `Depends()` 注入 UoW 和 Mediator
- 请求/响应模型用 Pydantic BaseModel
- 统一用 `ApiResponse` 包装响应

## 文件规则

- 每个文件只包含一个类/函数/概念（SRP）
- 命名: `create_user.py`（Command）、`create_user_handler.py`（Handler）
- 不创建 `dtos.py`、`utils.py`、`helpers.py` 这类杂物抽屉
