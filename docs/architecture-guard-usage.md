# 架构守护使用指南

架构守护通过 **import-linter** 与 **tests/architecture/** 下的 pytest 自动检查层内依赖、Handler 位置和 domain 实体/值对象继承。违反会导致 `make ci` 与 pre-commit 失败。

---

## 日常使用

### 提交前

与以往一样，提交/推送前在项目根目录执行：

```bash
make ci
```

其中已包含架构检查（`make architecture-check`）。也可单独跑架构守护：

```bash
make architecture-check
```

即：先执行 `lint-imports`，再执行 `pytest tests/architecture/ -v`。

### pre-commit

若已安装 pre-commit（`pre-commit install`），`git commit` 时会自动执行包括 `architecture-check` 在内的所有 hook。任一检查失败都会阻断提交，需修复后再提交。

---

## 新增业务模块时

### 1. 目录结构

沿用现有约定即可被守护：

- `domain/` — 聚合根、实体、值对象、领域事件、仓储接口
- `application/` — 其下必须有 `commands/`、`queries/` 子目录
- `infrastructure/` — 仓储实现、模型等
- `interfaces/`（可选）— API 路由等

可使用脚手架生成：`make new-module name=<模块名>`（参见 [scaffold-new-module.md](scaffold-new-module.md)）。

### 2. 注册到 import-linter

新模块需要纳入层边界检查时，在 **pyproject.toml** 的 `[tool.importlinter]` 中，给 `containers` 增加一行：

```toml
containers = [
    "app.shared_kernel",
    "app.modules.example",
    "app.modules.<新模块名>",   # 新增
]
```

### 3. Handler 放置

- 实现 **CommandHandler** 的类 → 放在 `application/commands/` 下（如 `*_handler.py`）
- 实现 **QueryHandler** 的类 → 放在 `application/queries/` 下

测试会自动扫描 `app.shared_kernel.application` 与 `app.modules.*.application`，无需修改测试代码。

### 4. Domain 类继承

- **实体/聚合根**：有 `id`、可变（非 frozen）→ 必须继承 `Entity` 或 `AggregateRoot`（来自 `app.shared_kernel.domain`）
- **值对象**：无 `id`、不可变（frozen dataclass）→ 必须继承 `ValueObject`
- 领域事件、异常类、Repository 接口等不强制继承上述基类

---

## 检查失败时如何修复

| 失败项 | 含义 | 处理方式 |
|--------|------|----------|
| **lint-imports** | 层依赖违规（如 domain 引用了 application） | 按报错中的 import 路径调整依赖方向，或将接口下沉到 domain |
| **test_command_handlers_live_in_commands_dir** | 某 CommandHandler 不在 `commands/` 下 | 将对应 Handler 文件移动到 `application/commands/` |
| **test_query_handlers_live_in_queries_dir** | 某 QueryHandler 不在 `queries/` 下 | 将对应 Handler 文件移动到 `application/queries/` |
| **test_entity_semantics_inherit_entity_or_aggregate_root** | 具实体语义的类未继承 Entity/AggregateRoot | 让该类继承 `Entity` 或 `AggregateRoot` |
| **test_value_object_semantics_inherit_value_object** | 具值对象语义的类未继承 ValueObject | 让该类继承 `ValueObject` |

断言消息会写出违规的类名与模块，按提示修改即可。

---

## 常用命令速查

| 命令 | 说明 |
|------|------|
| `make architecture-check` | 仅跑架构守护（import-linter + 架构 pytest） |
| `make ci` | 完整 CI（含架构守护） |
| `lint-imports` | 仅跑 import-linter |
| `pytest tests/architecture/ -v` | 仅跑架构相关 pytest |

---

## 相关文档

- [架构守护设计](plans/2026-02-19-architecture-guard-design.md)
- [架构守护实施计划](plans/2026-02-19-architecture-guard-implementation.md)
- [CLAUDE.md](../CLAUDE.md) — 项目概览与「架构守护」小节
