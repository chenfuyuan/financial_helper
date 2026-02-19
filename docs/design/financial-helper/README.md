# A股投资顾问系统设计文档

**日期：** 2026-02-19
**作者：** financial_helper 团队

---

## 文档索引

本目录包含 A 股投资顾问系统的完整设计文档，已按模块化方式拆分，便于 AI 编程工具按需读取。

### 核心文档

| 文档 | 说明 |
|------|------|
| [01-overview.md](./01-overview.md) | 项目概述、技术栈、整体架构、数据流、部署架构、演进路径、目录结构 |
| [02-dependencies.md](./02-dependencies.md) | 依赖关系图、模块边界约束、数据约束、LLM 约束 |

### 横向关注点

| 文档 | 说明 |
|------|------|
| [cross-cutting/error-handling.md](./cross-cutting/error-handling.md) | 错误处理策略、告警机制 |
| [cross-cutting/testing.md](./cross-cutting/testing.md) | 测试策略、测试分层、CI 流程 |
| [cross-cutting/security.md](./cross-cutting/security.md) | 安全设计、认证授权、数据安全 |
| [cross-cutting/performance.md](./cross-cutting/performance.md) | 性能优化策略、缓存策略、数据库优化 |
| [cross-cutting/operations.md](./cross-cutting/operations.md) | 运维与监控、健康检查、备份恢复 |

### 模块设计

| 文档 | 说明 |
|------|------|
| [modules/foundation.md](./modules/foundation.md) | 基础设施层（任务调度、爬虫、搜索引擎、通知、缓存、存储） |
| [modules/data-engineering.md](./modules/data-engineering.md) | 数据工程层（数据源管理、ETL、数据质量、数据仓库） |
| [modules/llm-gateway.md](./modules/llm-gateway.md) | LLM 网关层（模型管理、成本优化、请求处理） |
| [modules/knowledge-center.md](./modules/knowledge-center.md) | 知识中心（实体管理、图谱管理、知识推理） |
| [modules/market-insight.md](./modules/market-insight.md) | 市场洞察（趋势分析、情绪分析、异常检测） |
| [modules/coordinator.md](./modules/coordinator.md) | 协调器（LangGraph 流程编排、状态管理） |
| [modules/research.md](./modules/research.md) | 研究模块（宏观、财务、估值、催化剂、技术、行业分析） |
| [modules/debate.md](./modules/debate.md) | 辩论模块（多空博弈、风险评估） |
| [modules/judge.md](./modules/judge.md) | 决策模块（评分、置信度、买卖建议、仓位计算） |

---

## AI 编程使用指南

### 场景 1：实现新模块

当你要实现某个特定模块时（如 `research`），请读取以下文档：

1. **必须读取：**
   - `modules/research.md` - 研究模块详细设计
   - `02-dependencies.md` - 了解依赖关系和约束
   - `01-overview.md` - 了解整体架构

2. **按需读取：**
   - 相关的横向关注点文档（如 `cross-cutting/testing.md`）
   - 依赖的模块文档（如 `modules/data-engineering.md`）

### 场景 2：优化性能

当你要优化系统性能时，请读取：

- `cross-cutting/performance.md` - 性能优化策略
- 相关模块文档

### 场景 3：编写测试

当你要编写测试时，请读取：

- `cross-cutting/testing.md` - 测试策略
- 相关模块文档

### 场景 4：架构守护

当你要验证架构约束时，请读取：

- `02-dependencies.md` - 依赖关系和约束规则

---

## 原文档

本文档拆分自：`../2026-02-19-financial-helper-system-design.md`
