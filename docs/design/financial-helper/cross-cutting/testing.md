# 测试策略

**日期：** 2026-02-19
**作者：** financial_helper 团队

---

## 10. 测试策略

### 10.1 测试金字塔

```
        /\
       /E2E\        < 端到端测试 (API + UI)
      /------\
     /Integration\   < 集成测试 (多层协作)
    /------------\
   /    Unit      \  < 单元测试 (领域逻辑)
  ------------------
```

### 10.2 测试分层

#### 单元测试 (tests/unit/)
- **领域层测试**：纯业务逻辑，无外部依赖
  - Stock 实体测试
  - Report 实体测试
  - 领域服务测试
- **应用层测试**：Command/Query Handler，mock 外部依赖
  - Handler 测试
  - CQRS 测试

#### 集成测试 (tests/integration/)
- **数据访问集成测试**：使用 aiosqlite 内存数据库
  - Repository 集成测试
  - 数据库迁移测试
- **服务集成测试**：多模块协作
  - 分析流程集成测试
  - ETL 流程集成测试

#### API 测试 (tests/api/)
- **接口测试**：HTTP 调用 FastAPI
  - 使用 TestClient
  - 使用内存 SQLite
  - 测试示例见 `tests/api/modules/example/`

### 10.3 关键模块测试重点

#### FOUNDATION
- TaskScheduler：定时任务触发测试
- Crawler：爬虫稳定性测试、反爬策略测试
- Cache：缓存失效、缓存穿透、缓存雪崩测试
- Notification：多渠道通知测试

#### DATA_ENGINEERING
- DataSource：多数据源切换测试、限流降级测试
- ETL：脏数据处理测试、数据质量校验测试
- DataWarehouse：复杂查询性能测试

#### LLM_GATEWAY
- ModelManager：多模型路由测试、故障切换测试
- CostOptimizer：Token 计费测试、预算控制测试
- 集成测试：真实 LLM API 调用（CI 中可 mock）

#### COORDINATOR
- LangGraph：流程状态流转测试
- 断点续传测试
- 异常恢复测试

#### RESEARCH/DEBATE/JUDGE
- 各分析器单元测试（mock LLM）
- 提示词效果测试
- 输出格式验证测试

### 10.4 测试工具

| 用途 | 工具 |
|------|------|
| 测试框架 | pytest |
| Mock | unittest.mock |
| 异步测试 | pytest-asyncio |
| 测试数据 | factory_boy |
| 覆盖率 | pytest-cov |
| 性能测试 | locust |
| 模糊测试 | hypothesis |

### 10.5 CI 流程

```
提交代码
   ↓
代码检查 (ruff check)
   ↓
格式化检查 (ruff format --check)
   ↓
类型检查 (mypy)
   ↓
架构检查 (import-linter + pytest tests/architecture/)
   ↓
单元测试 (pytest tests/unit/)
   ↓
集成测试 (pytest tests/integration/)
   ↓
API 测试 (pytest tests/api/)
   ↓
合并
```
