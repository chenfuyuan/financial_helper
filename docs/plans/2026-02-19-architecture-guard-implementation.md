# 架构守护实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 用 import-linter + pytest 守护层内依赖与约定（Handler 位置、实体/值对象继承），CI 与 pre-commit 失败即阻断。

**Architecture:** 依赖规则由 import-linter 的 layered contract（containers: shared_kernel + modules.*）负责；Handler 放置与 domain 继承由 `tests/architecture/` 下的 pytest 负责。`make architecture-check` 先跑 import-linter 再跑架构测试；`make ci` 与 pre-commit 均调用该检查。

**Tech Stack:** Python 3.11, import-linter, pytest, pre-commit。

**设计文档:** `docs/plans/2026-02-19-architecture-guard-design.md`

---

## Task 1: 添加 import-linter 依赖与配置

**Files:**
- Modify: `pyproject.toml`
- Create: 无（配置写在 pyproject.toml）

**Step 1: 添加 dev 依赖**

在 `[project.optional-dependencies.dev]` 中增加一行：

```toml
  "import-linter>=2.0",
```

**Step 2: 添加 import-linter 配置**

在 `pyproject.toml` 末尾增加（若已有 `[tool.importlinter]` 则合并）：

```toml
[tool.importlinter]
root_package = "app"

[[tool.importlinter.contracts]]
name = "DDD layer boundaries"
type = "layers"
layers = [
    "(interfaces)",
    "application | infrastructure",
    "domain",
]
containers = [
    "app.shared_kernel",
    "app.modules.example",
]
```

说明：interfaces 可选（shared_kernel 无 interfaces）；application 与 infrastructure 同层互不依赖；domain 最底层。新模块加入时在 `containers` 中追加 `app.modules.<name>`。

**Step 3: 本地验证**

安装 dev 依赖并运行：

```bash
pip install -e ".[dev]"
lint-imports
```

Expected: 通过（无违反）。若失败，根据报错修正现有代码中的违规 import，再继续。

**Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "chore: add import-linter and layer contract config"
```

---

## Task 2: Handler 位置 pytest

**Files:**
- Create: `tests/architecture/__init__.py`（空或仅 `# architecture guard tests`）
- Create: `tests/architecture/test_handler_placement.py`
- Test: 同文件

**Step 1: 写失败测试（仅测“在 commands/ 下”的 CommandHandler）**

在 `tests/architecture/test_handler_placement.py` 中实现：

- 使用 `pkgutil.walk_packages` 或 `importlib.import_module` 遍历 `app.shared_kernel.application` 与 `app.modules.<name>.application`（通过扫描 `app.modules` 子包得到所有模块名）。
- 对每个 application 子模块，用 `inspect.getmembers(module, predicate=inspect.isclass)` 找出继承自 `CommandHandler` 或 `QueryHandler` 的类（需 import `app.shared_kernel.application.command_handler.CommandHandler` 与 `query_handler.QueryHandler`）。
- 断言：若类为 `CommandHandler` 子类，则其 `__module__` 包含 `.commands.`；若为 `QueryHandler` 子类，则 `__module__` 包含 `.queries.`。
- 测试用例名例如：`test_command_handlers_live_in_commands_dir`、`test_query_handlers_live_in_queries_dir`。

**Step 2: 运行测试确认失败或通过**

Run: `python -m pytest tests/architecture/test_handler_placement.py -v`

若当前代码已符合约定，应 PASS。若故意把某 Handler 移到错误路径再跑，应 FAIL。确认逻辑正确后恢复。

**Step 3: Commit**

```bash
git add tests/architecture/__init__.py tests/architecture/test_handler_placement.py
git commit -m "test(arch): add handler placement guard tests"
```

---

## Task 3: Domain 实体/值对象继承 pytest

**Files:**
- Create: `tests/architecture/test_domain_inheritance.py`
- Test: 同文件

**Step 1: 写测试逻辑**

- 遍历 `app.**.domain` 下模块（排除 `__init__.py` 若仅做 re-export）：通过 `pkgutil`/`importlib` 扫描 `app.shared_kernel.domain` 与 `app.modules.*.domain`。
- 对每个模块中的类（`inspect.getmembers(module, predicate=inspect.isclass)`）：
  - **实体语义**：dataclass 且非 frozen，且有 `id` 属性；或类名非 `*Event`/`*Exception` 且存在 `id` 属性。→ 必须继承 `Entity` 或 `AggregateRoot`（来自 `app.shared_kernel.domain`）。
  - **值对象语义**：dataclass 且 frozen 且无 `id` 属性，且类名非 `*Event`/`*Exception`。→ 必须继承 `ValueObject`。
- 排除：模块内从 `app.shared_kernel.domain` 来的 Entity/AggregateRoot/ValueObject 自身、Repository 接口、DomainEvent 子类、明显异常类。
- 断言失败时消息清晰，例如：`f"Domain class {cls.__name__} in {module.__name__} should inherit Entity/AggregateRoot"`。

**Step 2: 运行测试**

Run: `python -m pytest tests/architecture/test_domain_inheritance.py -v`

Expected: PASS（当前 example 的 Note 已继承 AggregateRoot）。若有误报，微调启发式（例如放宽“实体语义”条件）。

**Step 3: Commit**

```bash
git add tests/architecture/test_domain_inheritance.py
git commit -m "test(arch): add domain entity/value object inheritance guards"
```

---

## Task 4: make architecture-check 与 CI 集成

**Files:**
- Modify: `Makefile`

**Step 1: 新增 target**

在 `Makefile` 中增加：

```makefile
architecture-check: ## Run architecture guards (import-linter + pytest arch tests)
	lint-imports
	python -m pytest tests/architecture/ -v
```

并在 `.PHONY` 中加上 `architecture-check`。

**Step 2: 将架构检查纳入 ci**

在 `ci` target 中，在 `pytest` 之前或之后增加一行：

```makefile
	$(MAKE) architecture-check
```

或保持 `ci` 仅调用 `architecture-check` 代替单独跑 pytest 的架构部分，只要最终 `make ci` 包含：ruff、format check、mypy、全部测试（含架构）。建议：`ci` 中在 `pytest tests/ -v` 之前先执行 `architecture-check`，这样架构失败会先暴露。

更简单做法：不单独写 `architecture-check` 的依赖关系，让 `ci` 直接包含：
- `lint-imports`
- `python -m pytest tests/ -v`（已包含 tests/architecture/）

即把 `lint-imports` 加入 `ci`，并保证 `tests/architecture/` 在 `tests/` 下被 pytest 发现。二选一即可。

**Step 3: 本地跑 make ci**

Run: `make ci`

Expected: 全部通过。

**Step 4: Commit**

```bash
git add Makefile
git commit -m "ci: add architecture-check to make ci"
```

---

## Task 5: pre-commit hook

**Files:**
- Modify: `.pre-commit-config.yaml`

**Step 1: 添加 local hook**

在 `repos` 中增加一段（例如在 mypy 之后）：

```yaml
  - repo: local
    hooks:
      - id: architecture-check
        name: architecture-check
        entry: make architecture-check
        language: system
        pass_filenames: false
```

**Step 2: 验证**

Run: `pre-commit run architecture-check --all-files`

Expected: 通过。

**Step 3: Commit**

```bash
git add .pre-commit-config.yaml
git commit -m "chore: add architecture-check to pre-commit"
```

---

## Task 6: 文档说明

**Files:**
- Modify: `CLAUDE.md`

**Step 1: 在“关键约束”或“验证”附近增加一句**

例如在“关键约束”小节末尾增加一段：

```markdown
## 架构守护

- 层内依赖由 **import-linter** 检查（`lint-imports`）；Handler 位置与 domain 实体/值对象继承由 **tests/architecture/** 的 pytest 检查。
- 违反会导致 `make ci` 与 pre-commit 失败，需修复后才能合入。
- 新模块沿用 `domain/application/infrastructure/interfaces` 目录即可被守护；若使用枚举 container，需在 `pyproject.toml` 的 import-linter `containers` 中追加 `app.modules.<name>`。
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: document architecture guard in CLAUDE.md"
```

---

## 验收

- 运行 `make ci` 通过。
- 运行 `pre-commit run --all-files` 通过。
- 故意在 `app.modules.example.domain` 某文件中 `import app.modules.example.application`，运行 `lint-imports` 应失败。
- 将某 Handler 移出 commands/ 或 queries/，运行 `pytest tests/architecture/` 应失败。

---

Plan complete and saved to `docs/plans/2026-02-19-architecture-guard-implementation.md`.

**执行方式二选一：**

1. **Subagent-Driven（本会话）** — 按任务派发子 agent，每步完成后你做 review，再继续下一任务。  
2. **Parallel Session（新会话）** — 在新会话（建议用 executing-plans 的 worktree）中打开，按计划逐任务执行并在检查点做 review。

你选哪种？若选 1，我会用 subagent-driven-development 在本会话内按任务推进。
