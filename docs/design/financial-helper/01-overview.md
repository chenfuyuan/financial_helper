# A股投资顾问系统 - 项目概述

**日期：** 2026-02-19
**作者：** financial_helper 团队

---

## 1. 项目概述

基于 DDD + 整洁架构的 A 股投资顾问系统，提供数据抓取、LLM 分析、知识图谱、每日复盘等核心功能。

### 1.1 核心功能

- 数据抓取（tushare、akshare、网络爬虫）
- LLM 多维度分析（LangGraph 固定流程）
- 知识图谱构建与查询
- 每日复盘生成与推送

### 1.2 技术栈

| 组件 | 技术选型 |
|------|---------|
| Web 框架 | FastAPI |
| 关系型数据库 | PostgreSQL |
| 时序数据库 | InfluxDB |
| 图数据库 | Neo4j |
| 缓存 | Redis |
| 任务队列 | Celery + Redis |
| LLM 编排 | LangGraph |
| 爬虫框架 | Scrapy / Playwright |
| 搜索引擎 | Elasticsearch |
| 部署 | Docker Compose |

---

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                      接口层 (Interfaces)                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │   数据抓取    │  │   股票分析    │  │   知识图谱    │  ...           │
│  │    API       │  │    API       │  │    API       │               │
│  └──────────────┘  └──────────────┘  └──────────────┘               │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    应用层 (Application)                              │
│                                                                     │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │                    金融分析流程编排 (LangGraph)                │   │
│   │   ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐│   │
│   │   │ 研究分析 │───▶│ 多空辩论 │───▶│ 投资决策 │    │        ││   │
│   │   └─────────┘    └─────────┘    └─────────┘             │   │
│   └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      领域层 (Domain)                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                │
│  │   Stock    │  │   Report   │  │   Opinion   │  ...            │
│  │  (股票实体) │  │  (研究报告)  │  │  (多空观点)  │                │
│  └─────────────┘  └─────────────┘  └─────────────┘                │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   基础设施层 (Infrastructure)                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                      业务模块                                  │   │
│  │  data_engineering  │  llm_gateway  │  knowledge_center  │   │
│  │  market_insight  │  coordinator   │  foundation        │   │
│  │  research        │  debate        │  judge             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │PostgreSQL│  │ InfluxDB │  │  Neo4j   │  │  Redis   │        │
│  │ (关系型) │  │ (时序型) │  │(图数据)  │  │ (缓存)   │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 5. 数据流设计

### 5.1 数据抓取流程

```
1. 定时任务触发 (task_scheduler)
   ↓
2. 调用数据源 (data_source_manager)
   ├─ Tushare API
   ├─ AkShare API
   └─ Web Crawler (调用 foundation.crawler)
   ↓
3. ETL 处理 (etl_pipeline)
   ├─ 数据清洗
   ├─ 格式标准化
   └─ 数据融合
   ↓
4. 数据质量检测 (data_quality)
   ↓
5. 存储到数据仓库 (data_warehouse)
   ├─ PostgreSQL (结构化数据)
   ├─ InfluxDB (时序数据)
   └─ 触发领域事件
```

### 5.2 分析流程

```
1. 触发分析请求
   ↓
2. COORDINATOR 启动 LangGraph 流程
   ↓
3. RESEARCH 生成研究报告
   ├─ 从 DATA_ENGINEERING 获取数据
   ├─ 从 MARKET_INSIGHT 获取市场洞察
   ├─ 从 KNOWLEDGE_CENTER 获取知识
   └─ 调用 LLM_GATEWAY 生成报告
   ↓
4. DEBATE 进行多空辩论
   ├─ 从 KNOWLEDGE_CENTER 获取知识
   └─ 调用 LLM_GATEWAY 进行辩论
   ↓
5. JUDGE 做出决策
   ├─ 从 KNOWLEDGE_CENTER 获取知识
   └─ 调用 LLM_GATEWAY 辅助决策
   ↓
6. 生成最终分析结果
   ↓
7. 存储结果 + 发送通知 (foundation.notification)
```

### 5.3 每日复盘流程

```
1. 定时任务触发 (task_scheduler)
   ↓
2. 收集当日市场数据 (DATA_ENGINEERING)
   ↓
3. 对关注股票批量运行分析流程 (COORDINATOR)
   ↓
4. 汇总分析结果，生成复盘报告
   ↓
5. 存储报告 + 推送通知 (foundation.notification)
```

---

## 6. 部署架构

### 6.1 Docker Compose 服务

```yaml
services:
  web:
    # FastAPI 应用服务
  db:
    # PostgreSQL (业务数据)
  influxdb:
    # InfluxDB (时序数据)
  neo4j:
    # Neo4j (知识图谱)
  redis:
    # Redis (缓存 + Celery Broker)
  elasticsearch:
    # Elasticsearch (搜索引擎)
  celery-worker:
    # Celery Worker
  celery-beat:
    # Celery Beat (定时任务)
```

---

## 8. 演进路径

### 阶段一：MVP
- 实现核心数据抓取（Tushare + AkShare）
- 实现基础分析流程（Research → Debate → Judge）
- 实现每日复盘功能

### 阶段二：增强
- 实现知识图谱
- 实现市场洞察模块
- 实现更复杂的 LangGraph 流程

### 阶段三：扩展
- 扩展到全市场（港股、美股）
- 增加更多分析维度
- 优化性能和成本

---

## 14. 目录结构（补充）

```
src/app/modules/
├── foundation/
│   ├── domain/
│   ├── application/
│   ├── infrastructure/
│   │   ├── task_scheduler/
│   │   ├── crawler/
│   │   ├── search_engine/
│   │   ├── notification/
│   │   ├── cache/
│   │   └── storage/
│   └── interfaces/
│
├── data_engineering/
│   ├── domain/
│   ├── application/
│   ├── infrastructure/
│   │   ├── data_source_manager/
│   │   ├── etl_pipeline/
│   │   ├── data_quality/
│   │   └── data_warehouse/
│   └── interfaces/
│
├── llm_gateway/
│   ├── domain/
│   ├── application/
│   ├── infrastructure/
│   │   ├── model_manager/
│   │   ├── cost_optimizer/
│   │   └── request_handler/
│   └── interfaces/
│
├── knowledge_center/
│   ├── domain/
│   ├── application/
│   ├── infrastructure/
│   │   ├── entity_manager/
│   │   ├── graph_manager/
│   │   └── knowledge_reasoner/
│   └── interfaces/
│
├── market_insight/
│   ├── domain/
│   ├── application/
│   ├── infrastructure/
│   │   ├── trend_analyzer/
│   │   ├── sentiment_analyzer/
│   │   └── anomaly_detector/
│   └── interfaces/
│
├── coordinator/
│   ├── domain/
│   ├── application/
│   │   ├── langgraph_workflow/
│   │   ├── state_manager/
│   │   └── workflow_executor/
│   ├── infrastructure/
│   └── interfaces/
│
├── research/
│   ├── domain/
│   ├── application/
│   │   ├── macro_analyzer/
│   │   ├── financial_analyzer/
│   │   ├── valuation_analyzer/
│   │   ├── catalyst_analyzer/
│   │   ├── technical_analyzer/
│   │   ├── industry_analyzer/
│   │   └── report_generator/
│   ├── infrastructure/
│   └── interfaces/
│
├── debate/
│   ├── domain/
│   ├── application/
│   │   ├── bull_agent/
│   │   ├── bear_agent/
│   │   ├── debate_engine/
│   │   └── risk_assessor/
│   ├── infrastructure/
│   └── interfaces/
│
└── judge/
    ├── domain/
    ├── application/
    │   ├── scorer/
    │   ├── confidence_evaluator/
    │   ├── decision_maker/
    │   └── position_sizer/
    ├── infrastructure/
    └── interfaces/
```
