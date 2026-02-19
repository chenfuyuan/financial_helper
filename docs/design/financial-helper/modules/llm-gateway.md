# LLM_GATEWAY（LLM 网关层）

**日期：** 2026-02-19
**作者：** financial_helper 团队

---

## 3.3 LLM_GATEWAY（LLM 网关层）

**职责：** 统一管理所有 LLM 服务的接入，提供统一的 API 接口和治理能力。

**核心约束：**
1. **只提供大模型调用能力** - 具体业务逻辑在其他业务模块
2. **不进行提示词管理** - 提示词完全由业务模块管理
3. **不依赖 DATA_ENGINEERING** - 独立的数据访问路径

**子模块：**
- `model_manager` - 模型管理器（多厂商接入、路由、故障切换）
- `cost_optimizer` - 成本优化器（Token优化、缓存策略）
- `request_handler` - 请求处理器（流式、批量、异步）

**暴露接口：**
- `LLMGateway.chat(model, messages, params) -> LLMResponse`
- `LLMGateway.stream_chat(model, messages) -> StreamIterator`
- `LLMGateway.batch_chat(requests) -> List[LLMResponse]`
- `ModelManager.get_available_models() -> List[ModelInfo]`

**依赖：**
- ↳ FOUNDATION (cache, notification)

**被依赖：**
- ◀ COORDINATOR (调用 LLM 进行分析流程编排)
- ◀ RESEARCH (调用 LLM 生成研究报告)
- ◀ DEBATE (调用 LLM 进行多空辩论)
- ◀ JUDGE (调用 LLM 进行决策判断)

**禁止：**
- ✗ 直接调用外部 API（应通过 model_manager 统一路由）
- ✗ 访问业务数据库（只管理 prompt 和模型配置）
- ✗ 包含分析逻辑（只提供 LLM 能力，不做业务分析）
- ✗ 依赖 DATA_ENGINEERING（保持独立）
