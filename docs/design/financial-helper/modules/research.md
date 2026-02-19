# RESEARCH（研究模块）

**日期：** 2026-02-19
**作者：** financial_helper 团队

---

## 3.7 RESEARCH（研究模块）

**职责：** 生成研究报告（宏观分析、财务分析、估值分析、催化剂分析、技术分析等）。

**子模块：**
- `macro_analyzer` - 宏观分析器
  - 宏观经济指标分析（GDP、CPI、PMI 等）
  - 货币政策分析（利率、流动性等）
  - 政策环境分析（行业政策、监管动态）
  - 市场情绪分析（恐慌指数、资金流向等）
- `financial_analyzer` - 财务分析器
  - 财务报表分析（资产负债表、利润表、现金流量表）
  - 财务指标分析（ROE、ROA、毛利率、净利率等）
  - 成长性分析（营收增长、利润增长等）
  - 财务健康度分析（偿债能力、现金流质量）
  - 财报勾稽关系校验
  - 异常财务指标识别
- `valuation_analyzer` - 估值分析器
  - 绝对估值模型（DCF、DDM）
  - 相对估值模型（PE、PB、PS、EV/EBITDA）
  - 估值历史分位分析
  - 行业估值对比
  - 估值安全边际评估
- `catalyst_analyzer` - 催化剂分析器
  - 重大事件跟踪（并购、重组、股权激励等）
  - 业绩预告和快报分析
  - 机构调研动向
  - 股东增减持分析
  - 分析师评级变化
  - 新闻舆情监控
- `technical_analyzer` - 技术分析器
  - 趋势分析（均线、趋势线、通道）
  - 技术指标（MACD、KDJ、RSI、布林带等）
  - 形态识别（头肩顶/底、双顶/底、三角形整理等）
  - 量价分析（成交量、换手率、资金流向）
  - 支撑阻力位分析
  - 筹码结构分析
- `industry_analyzer` - 行业分析器
  - 行业生命周期分析
  - 行业竞争格局（波特五力模型）
  - 产业链分析（上下游关系）
  - 行业景气度分析
  - 行业政策解读
- `report_generator` - 报告生成器
  - 多维度分析结果整合
  - 结构化报告生成
  - Markdown/PDF 报告输出

**暴露接口：**
- `Research.analyze(code) -> ResearchReport`
- `Research.macro_analysis() -> MacroReport`
- `Research.financial_analysis(code) -> FinancialReport`
- `Research.valuation_analysis(code) -> ValuationReport`
- `Research.catalyst_analysis(code) -> CatalystReport`
- `Research.technical_analysis(code) -> TechnicalReport`
- `Research.industry_analysis(industry_code) -> IndustryReport`

**依赖：**
- ↳ DATA_ENGINEERING (获取数据)
- ↳ LLM_GATEWAY (调用 LLM 生成报告)
- ↳ KNOWLEDGE_CENTER (获取知识)
- ↳ MARKET_INSIGHT (获取市场洞察)

**被依赖：**
- ◀ COORDINATOR (调用研究模块)

**禁止：**
- ✗ 直接调用外部 LLM API（应通过 llm_gateway）
- ✗ 包含决策逻辑（只生成研究报告，不做投资建议）
