# CLAUDE.md

## 项目

**金融助手系统** - 基于 DDD + 整洁架构的 A 股投资顾问系统，提供数据抓取、LLM 分析、知识图谱、每日复盘等核心功能。

**技术栈:** Python 3.11, FastAPI, SQLAlchemy (async + asyncpg), PostgreSQL, InfluxDB, Neo4j, Redis, Celery, LangGraph, Elasticsearch, Alembic, pydantic-settings, structlog, pytest

## 设计文档索引

在开始任何开发工作前，请先查阅相关设计文档。文档已按模块化拆分，按需读取：

### 核心文档（必读）
- `docs/design/financial-helper/README.md` - 设计文档总索引 + AI 使用指南
- `docs/design/financial-helper/01-overview.md` - 项目概述、技术栈、整体架构、数据流
- `docs/design/financial-helper/02-dependencies.md` - 依赖关系图、模块边界约束

### 模块文档（按需要读取）
实现特定模块时，请读取对应的模块设计文档：
- `docs/design/financial-helper/modules/foundation.md` - 基础设施层
- `docs/design/financial-helper/modules/data-engineering.md` - 数据工程层
- `docs/design/financial-helper/modules/llm-gateway.md` - LLM 网关层
- `docs/design/financial-helper/modules/knowledge-center.md` - 知识中心
- `docs/design/financial-helper/modules/market-insight.md` - 市场洞察
- `docs/design/financial-helper/modules/coordinator.md` - 协调器（LangGraph 流程编排）
- `docs/design/financial-helper/modules/research.md` - 研究模块
- `docs/design/financial-helper/modules/debate.md` - 辩论模块
- `docs/design/financial-helper/modules/judge.md` - 决策模块

### 横向关注点（按需要读取）
- `docs/design/financial-helper/cross-cutting/error-handling.md` - 错误处理策略
- `docs/design/financial-helper/cross-cutting/testing.md` - 测试策略
- `docs/design/financial-helper/cross-cutting/security.md` - 安全设计
- `docs/design/financial-helper/cross-cutting/performance.md` - 性能优化策略
- `docs/design/financial-helper/cross-cutting/operations.md` - 运维与监控

### AI 工作流建议
1. **实现新功能**：先读对应模块文档 + 02-dependencies.md + 01-overview.md
2. **编写测试**：先读 cross-cutting/testing.md + 对应模块文档
3. **优化性能**：先读 cross-cutting/performance.md
4. **架构检查**：先读 02-dependencies.md 了解约束规则

## 代码开发时

开发规范已沉淀为 Cursor Rules（`.cursor/rules/`），编辑匹配文件时自动加载，无需手动阅读：

| Rule | 触发 glob | 职责 |
|------|----------|------|
| `architecture-guard` | `src/**/*.py` | DDD 分层、领域建模、文件规则 |
| `testing-conventions` | `tests/**/*.py` | 测试目录、TDD 流程、反模式 |
| `logging-standards` | `src/**/*.py` | structlog 日志规范 |
| `docstring-standards` | `**/*.py` | 注释与 Attributes 文档 |
| `database-model` | `src/**/models/**/*.py` | ORM 字段顺序、禁止外键 |
| `dependency-injection` | `src/**/interfaces/**/*.py` | DI 分工、模块注册 |

另有两个 Skills（`.cursor/skills/`）按需触发：
- **ddd-module-scaffold** — 创建新模块时的脚手架流程
- **pre-commit-verify** — 提交前验证清单（`make ci` 必须通过才能 commit）

> 原始规范文档保留在 `guide/` 目录供人类阅读，Rules/Skills 是 AI 执行时的权威来源。

## 节省 Token（AI 操作）

- **移动/重命名文件**：优先「移动文件再在目标位置修改」，避免「先写新文件再删旧文件」，减少重复内容与 token 消耗。
- **修改文档**：先阅读相关章节，将变更融入既有结构（合并到对应段落或小节），避免在文末堆叠不连贯的新段落；仅新增独立小节时可追加。