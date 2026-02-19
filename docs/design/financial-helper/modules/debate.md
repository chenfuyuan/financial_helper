# DEBATE（辩论模块）

**日期：** 2026-02-19
**作者：** financial_helper 团队

---

## 3.8 DEBATE（辩论模块）

**职责：** 对研究报告进行多空博弈（多头观点、空头观点、观点碰撞、风险评估）。

**子模块：**
- `bull_agent` - 多头代理
- `bear_agent` - 空头代理
- `debate_engine` - 辩论引擎
- `risk_assessor` - 风险评估器

**暴露接口：**
- `Debate.debate(research_report) -> DebateResult`

**依赖：**
- ↳ LLM_GATEWAY (调用 LLM 进行辩论)
- ↳ KNOWLEDGE_CENTER (获取知识支撑观点)

**被依赖：**
- ◀ COORDINATOR (调用辩论模块)

**禁止：**
- ✗ 直接调用外部 LLM API（应通过 llm_gateway）
- ✗ 做出最终决策（只呈现多空观点，不做最终判断）
