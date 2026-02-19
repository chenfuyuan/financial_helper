# MARKET_INSIGHT（市场洞察）

**日期：** 2026-02-19
**作者：** financial_helper 团队

---

## 3.5 MARKET_INSIGHT（市场洞察）

**职责：** 市场趋势分析、情绪监测、异常检测。

**子模块：**
- `trend_analyzer` - 趋势分析器（技术指标、形态识别、量价分析）
- `sentiment_analyzer` - 情绪分析器（舆情监控、情绪指标、预期差分析）
- `anomaly_detector` - 异常检测器（异动检测、黑天鹅识别）

**暴露接口：**
- `TrendAnalyzer.analyze(code, period) -> TrendReport`
- `SentimentAnalyzer.analyze(code) -> SentimentScore`
- `AnomalyDetector.detect(market_data) -> List[Anomaly]`

**依赖：**
- ↳ FOUNDATION (cache)
- ↳ DATA_ENGINEERING (获取市场数据)

**被依赖：**
- ◀ RESEARCH (获取市场洞察用于研究报告)
- ◀ COORDINATOR (获取市场洞察)

**禁止：**
- ✗ 直接调用 LLM（应通过 llm_gateway）
- ✗ 包含投资建议（只提供洞察指标，不做决策）
