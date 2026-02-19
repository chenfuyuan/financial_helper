# JUDGE（决策模块）

**日期：** 2026-02-19
**作者：** financial_helper 团队

---

## 3.9 JUDGE（决策模块）

**职责：** 决策判断（综合评分、置信度评估、买卖建议、仓位建议）。

**子模块：**
- `scorer` - 评分器
- `confidence_evaluator` - 置信度评估器
- `decision_maker` - 决策器
- `position_sizer` - 仓位计算器

**暴露接口：**
- `Judge.judge(debate_result) -> Decision`

**依赖：**
- ↳ LLM_GATEWAY (调用 LLM 辅助决策)
- ↳ KNOWLEDGE_CENTER (获取知识)

**被依赖：**
- ◀ COORDINATOR (调用决策模块)

**禁止：**
- ✗ 直接调用外部 LLM API（应通过 llm_gateway）
