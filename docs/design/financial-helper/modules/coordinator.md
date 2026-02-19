# COORDINATOR（协调器）

**日期：** 2026-02-19
**作者：** financial_helper 团队

---

## 3.6 COORDINATOR（协调器）

**职责：** 金融分析流程编排（LangGraph 固定流程），连接各业务模块。

**核心约束：**
1. **不依赖数据** - 数据由各业务模块自行获取
2. **不调用 LLM** - LLM 调用由各业务模块自行处理
3. **只进行流程编排** - 负责工作流的定义和状态流转

**子模块：**
- `langgraph_workflow` - LangGraph 工作流定义
- `state_manager` - 状态管理器
- `workflow_executor` - 工作流执行器

**分析流程：**
```
[准备数据] → [研究分析] → [多空辩论] → [决策判断] → [报告生成]
   ↓              ↓             ↓             ↓             ↓
 各业务模块     Research      Debate       Judge         汇总输出
 自行获取       自行调用      自行调用     自行调用
 数据          LLM          LLM          LLM
```

**暴露接口：**
- `Coordinator.run_analysis(code) -> AnalysisResult`
- `Coordinator.daily_review(date) -> ReviewReport`

**依赖：**
- ↳ RESEARCH (调用研究模块)
- ↳ DEBATE (调用辩论模块)
- ↳ JUDGE (调用决策模块)
- ↳ FOUNDATION (task_scheduler, notification)

**被依赖：**
- ◀ 接口层 (API)

**禁止：**
- ✗ 包含具体分析逻辑（应委托给各业务模块）
- ✗ 直接调用外部 API（应通过各业务模块）
- ✗ 直接访问 DATA_ENGINEERING（由业务模块自行访问）
- ✗ 直接调用 LLM_GATEWAY（由业务模块自行调用）
