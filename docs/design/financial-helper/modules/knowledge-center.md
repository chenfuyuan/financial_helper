# KNOWLEDGE_CENTER（知识中心）

**日期：** 2026-02-19
**作者：** financial_helper 团队

---

## 3.4 KNOWLEDGE_CENTER（知识中心）

**职责：** 知识图谱构建、管理和查询，提供知识推理能力。

**子模块：**
- `entity_manager` - 实体管理器（实体抽取、关系构建）
- `graph_manager` - 图谱管理器（图数据库操作、路径查询、相似度计算）
- `knowledge_reasoner` - 知识推理器（基于图谱的推理和发现）

**暴露接口：**
- `EntityManager.extract_entities(text) -> List[Entity]`
- `EntityManager.add_relation(entity1, relation, entity2)`
- `GraphManager.query_relations(entity, depth) -> Graph`
- `GraphManager.find_path(entity1, entity2) -> Path`
- `KnowledgeReasoner.infer(question) -> Answer`

**依赖：**
- ↳ FOUNDATION (search_engine, cache)
- ↳ DATA_ENGINEERING (获取原始数据)

**被依赖：**
- ◀ RESEARCH (获取知识用于研究分析)
- ◀ DEBATE (获取知识支撑观点)
- ◀ JUDGE (获取知识辅助决策)

**禁止：**
- ✗ 直接调用 LLM（应通过 llm_gateway）
- ✗ 包含业务分析逻辑（只提供知识检索和推理）
