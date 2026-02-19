# 架构守护测试设计

**日期：** 2026-02-19  
**目标：** 用自动化手段守护分层与约定，防止架构腐化；一次编写，CI + pre-commit 长期生效。

---

## 1. 背景与范围

### 1.1 现状

- 项目有清晰的分层与目录约定（CLAUDE.md、ddd-best-practices.md），但**全靠人遵守**，无自动检查。
- 依赖方向为：`interfaces → application → domain ← infrastructure`，domain 零外部依赖。

### 1.2 目标

- **层内依赖**：每个包（shared_kernel、各 module）内，禁止违反上述依赖方向。
- **约定**：CommandHandler/QueryHandler 必须在指定目录；domain 中实体/值对象必须继承对应基类。
- **失败即阻断**：违反时 CI 与 pre-commit 均失败，必须修复才能通过。

### 1.3 不守范围

- **不**限制模块间谁 import 谁（例如 `modules.foo` 与 `modules.bar` 之间的依赖不在此次守护内）。

---

## 2. 依赖方向（铁律）

```
interfaces → application → domain ← infrastructure
```

| 层            | 不得 import |
|---------------|-------------|
| domain        | application, infrastructure, interfaces |
| application   | infrastructure, interfaces |
| infrastructure| application, interfaces |
| interfaces    | （可依赖 application, infrastructure, domain） |

---

## 3. 守护规则

### 3.1 层内依赖（import-linter）

- **工具**：import-linter，layered contract。
- **分层模型**：在根包 `app` 下按目录名抽象出四层，不区分 shared_kernel 与具体 module，只认路径：
  - **interfaces**：`app.**.interfaces`（以及顶层 `app.interfaces`）
  - **application**：`app.**.application`
  - **infrastructure**：`app.**.infrastructure`
  - **domain**：`app.**.domain`
- **层顺序（高→低）**：interfaces 为最高层，application 与 infrastructure 同层且互不依赖，domain 为最低层。
- **配置要点**：
  - 使用 **containers**：`app.shared_kernel` 与 `app.modules.*`（或枚举各 module），使每个“包”内复用同一套层定义。
  - 层列表（高到低）：`(interfaces) | application | infrastructure | domain`。interfaces 用括号表示可选（shared_kernel 无 interfaces 子包）。
  - 若 import-linter 不支持 containers 通配符，则新模块加入时在配置中追加一个 container 即可，或通过脚本生成配置。

### 3.2 Handler 位置（pytest）

- **规则**：
  - 实现 `CommandHandler` 的类必须位于 `application/commands/` 目录下。
  - 实现 `QueryHandler` 的类必须位于 `application/queries/` 目录下。
- **范围**：`app.shared_kernel` 与 `app.modules.*` 下的 application 子包。
- **实现**：遍历上述包，用 `inspect` 或 ast 找出 Handler 子类，根据 `__module__` 或文件路径断言目录为 `commands` 或 `queries`。

### 3.3 实体/值对象继承（pytest）

- **范围**：仅 `app.**.domain` 下的模块（排除仅做 re-export 的 `__init__.py`）。
- **规则**：
  - 具「实体语义」的类必须继承 `Entity` 或 `AggregateRoot`（来自 shared_kernel.domain）。
  - 具「值对象语义」的类必须继承 `ValueObject`。
- **启发式**（避免误伤事件/异常/DTO）：
  - **实体**：有 `id` 属性且非 `dataclass(frozen=True)`；或类名符合常见聚合根命名且非 `*Event` / `*Exception`。
  - **值对象**：`dataclass(frozen=True)` 且无 `id`，且类名不是 `*Event` / `*Exception`。
- 领域事件、异常、仓储接口等不强制继承基类，仅对“像实体/聚合根”和“像值对象”的类做继承检查。

---

## 4. 实现与集成

### 4.1 组件与放置

| 组件 | 位置 / 方式 |
|------|--------------|
| import-linter 配置 | `pyproject.toml` 的 `[tool.importlinter]`（或项目根 `.importlinter`） |
| 架构 pytest | `tests/architecture/`：`test_handler_placement.py`、`test_domain_inheritance.py` |
| 入口命令 | `make architecture-check`：先运行 import-linter，再 `pytest tests/architecture/ -v` |
| CI | `make ci` 中加入 `architecture-check`（或等价：import-linter + 将架构测试纳入 `make test`） |
| pre-commit | 新增 local hook，执行 `make architecture-check` |

### 4.2 依赖

- 将 `import-linter` 加入 `[project.optional-dependencies.dev]`，CI 与 pre-commit 使用 dev 依赖即可。

### 4.3 错误与可读性

- **import-linter 失败**：输出违反的 import 与层名。
- **pytest 失败**：断言信息明确标出违反的类/模块与规则（例如：`CommandHandler 子类 X 必须在 application/commands/ 下`）。

### 4.4 文档

- 在 CLAUDE.md 或 docs 中增加简短说明：架构守护由 import-linter（层内依赖）+ `tests/architecture/`（Handler 位置、实体/值对象继承）组成，违反则 CI 与 pre-commit 失败。
- 新模块只要沿用 `domain/application/infrastructure/interfaces` 目录结构即被自动守护；若使用枚举 container，新模块需在 import-linter 配置中追加一条。

---

## 5. 验收

- 在现有 example 模块上，所有守护通过。
- 故意在 domain 中 import application，或把某 Handler 移出 commands/，CI 与 pre-commit 均失败且报错清晰。
- `make ci` 与 pre-commit 均包含架构检查，通过后方可合入。

---

*下一步：调用 writing-plans 生成实施计划。*
