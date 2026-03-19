---
name: ddd-module-scaffold
description: >-
  创建新业务模块的标准四层目录脚手架。当用户说"创建新模块"、"新增模块"、
  "添加模块"或需要搭建 DDD 模块结构时使用。
---

# DDD 模块脚手架

创建新的业务模块时，严格按以下步骤执行。

## 步骤清单

1. **确认模块名**：小写下划线命名，如 `market_insight`
2. **创建标准四层目录**（见下方模板）
3. **在每个 `__init__.py` 中留空**（或按需导出公共接口）
4. **注册模块 Router** 到 `app/interfaces/module_registry.py`
5. **若模块用枚举 container**，在 `pyproject.toml` 的 import-linter `containers` 中追加 `app.modules.<name>`
6. **运行 `make ci`** 验证架构守护通过

## 目录模板

```
src/app/modules/<module_name>/
├── __init__.py
├── domain/
│   ├── __init__.py
│   ├── entities/
│   │   └── __init__.py
│   ├── value_objects/
│   │   └── __init__.py
│   ├── gateways/
│   │   └── __init__.py
│   ├── repositories/
│   │   └── __init__.py
│   ├── services/
│   │   └── __init__.py
│   ├── events/
│   │   └── __init__.py
│   └── exceptions.py
├── application/
│   ├── __init__.py
│   ├── commands/
│   │   └── __init__.py
│   ├── queries/
│   │   └── __init__.py
│   └── events/
│       └── __init__.py
├── infrastructure/
│   ├── __init__.py
│   ├── models/
│   │   └── __init__.py
│   ├── gateways/
│   │   ├── __init__.py
│   │   └── mappers/
│   │       └── __init__.py
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── mappers/
│   │       └── __init__.py
│   ├── cache/
│   │   └── __init__.py
│   └── tasks/
│       └── __init__.py
└── interfaces/
    ├── __init__.py
    ├── api/
    │   └── __init__.py
    ├── consumers/
    │   └── __init__.py
    ├── schedulers/
    │   └── __init__.py
    └── dependencies.py
```

## 注册到 module_registry.py

在 `app/interfaces/module_registry.py` 的 `_collect_module_routers()` 中追加：

```python
from app.modules.<module_name>.interfaces.api.<router_file> import router as <module_name>_router

routers.append(("<module_name>", <module_name>_router))
```

## 对应测试目录

同步创建测试目录：

```
tests/unit/modules/<module_name>/
├── domain/
└── application/
tests/integration/modules/<module_name>/
tests/api/modules/<module_name>/
```

## 验证

创建完成后运行 `make ci` 确保 import-linter 与架构测试通过。
