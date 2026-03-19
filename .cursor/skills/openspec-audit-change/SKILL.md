---
name: openspec-audit-change
description: Audit OpenSpec change artifacts for quality, completeness, and cross-artifact consistency. Use when the user wants to review, audit, or optimize existing proposal/spec/design documents.
license: MIT
metadata:
  author: project
  version: "1.0"
---

Audit the quality of OpenSpec change artifacts and optionally generate optimized versions.

**Input**: A change name or directory path. If omitted, prompt for selection.

**Steps**

1. **Locate the change**

   If no change name provided, run `openspec list --json` and use **AskUserQuestion** to let the user select.

   Read all artifacts in the change directory:
   - `openspec/changes/<name>/proposal.md`
   - `openspec/changes/<name>/specs/<capability>/spec.md` (all spec files)
   - `openspec/changes/<name>/design.md`
   - `openspec/changes/<name>/pre_design.md` (if exists, for context only)

   Also read relevant codebase files referenced in the artifacts (existing Commands, Handlers, Repositories, etc.) to ground the review.

2. **Audit proposal.md — 提案质量检查**

   Use **TodoWrite** to track each check item.

   | # | 检查项 | 标准 |
   |---|--------|------|
   | P1 | 动机量化 | Why 中的每个痛点有数据支撑（频率、耗时、成本、影响范围），无"体验不好""大量"等纯定性词 |
   | P2 | 范围切割 | 显式包含 In Scope 和 Out of Scope 两个章节 |
   | P3 | What Changes 动词开头 | 每条以「新增/修改/移除」开头 |
   | P4 | Capabilities 命名 | name 为 kebab-case 英文，描述为中文 |
   | P5 | 风险表格 | 包含 Risks 章节，表格至少 3 行，含至少 1 个非功能性风险 |
   | P6 | 量化 Impact | Impact 中的运行时影响有数字估算（如 API 调用量、数据库写入量） |

3. **Audit spec.md — 规格质量检查（核心，最严格）**

   以"魔鬼测试工程师"视角审查，同时检查格式与内容。

   | # | 检查项 | 标准 |
   |---|--------|------|
   | S1 | Requirement 标题格式 | 每个标题以 MUST / SHALL / MAY 开头 |
   | S2 | Scenario 三段式 | 每个 Scenario 包含 GIVEN / WHEN / THEN |
   | S3 | 异常场景覆盖 | 整个 spec 至少 3 个异常/边界场景（超时、认证失败、输入校验、数据依赖缺失、并发等） |
   | S4 | 每 Requirement 覆盖 | 至少 1 个正常 + 1 个边界/异常 Scenario |
   | S5 | 消除模糊 | 无"快速""友好""合理"等主观词，均已量化 |
   | S6 | 接口契约 | Result / 返回值用字段表格（字段、类型、说明）定义 |
   | S7 | 输入校验 | 对外参数有校验需求和对应 Scenario |
   | S8 | 分隔符 | 不同 Requirement 用 `---` 分隔 |
   | S9 | ADDED/MODIFIED/REMOVED 标记 | 有区分变更类型的章节标题 |

   **魔鬼测试场景清单**（逐一检查是否遗漏）：
   - 网络超时 / 外部服务不可达
   - 认证失败 / Token 过期
   - 输入参数边界值（空、极大、未来日期、负数）
   - 数据依赖缺失（上游数据为空或不完整）
   - 并发执行 / 重复调用
   - 长时间运行中的资源耗尽
   - start == end 等边界相等情况

4. **Audit design.md — 设计质量检查**

   | # | 检查项 | 标准 |
   |---|--------|------|
   | D1 | Goals/Non-Goals 对齐 | Non-Goals 与 proposal Out of Scope 一致 |
   | D2 | 决策 Trade-off | 每个 Decision 包含对比表（维度、选择方案、备选方案）|
   | D3 | 单点故障分析 | Architecture 章节含 SPOF 分析表 |
   | D4 | API Schema | 包含 Command / Result / Repository 扩展的 dataclass 定义 |
   | D5 | 错误码表 | 错误场景、异常类型、说明的表格 |
   | D6 | 数据流 | 有 ASCII 流程图或数据流描述 |
   | D7 | Migration Plan | 含分阶段计划 + 回滚策略 |

5. **三位一体一致性检查**

   | # | 检查项 | 方法 |
   |---|--------|------|
   | C1 | Proposal → Spec 覆盖 | 每项 In Scope 对应至少一个 Spec Requirement |
   | C2 | Proposal Risk → Spec/Design | 每条风险有缓解决策（Design Decision）或异常场景（Spec Scenario）|
   | C3 | Spec → Design 支撑 | 每个 Requirement 有对应 Decision |
   | C4 | Result 字段对齐 | Spec 的字段表与 Design API Schema 的字段名、类型完全一致 |
   | C5 | 术语统一 | Command 名、字段名、方法名全文无别名歧义 |

6. **生成审核报告**

   ```markdown
   ## 审核报告: <change-name>

   ### 总览
   | 维度 | 通过 | 警告 | 严重 |
   |------|------|------|------|
   | Proposal 质量 | X/6 | Y | Z |
   | Spec 质量 | X/9 | Y | Z |
   | Design 质量 | X/7 | Y | Z |
   | 一致性 | X/5 | Y | Z |

   ### 严重问题（必须修复）
   - ...

   ### 警告（建议修复）
   - ...

   ### 建议（锦上添花）
   - ...
   ```

7. **询问用户下一步**

   Use **AskUserQuestion** with options:
   - "生成优化后的文件（`*_optimized.md`）"
   - "仅保留报告，我自己手动修改"
   - "直接覆盖原文件（需确认）"

   If user chooses to generate optimized files:
   - 为每个不合格的文件生成 `<name>_optimized.md`
   - 在每个关键修改处用 `<!-- REASON: 说明 -->` 标注修改理由
   - 保持文件结构与 openspec-docs.mdc 规则一致

**Quality Heuristics**

- **严重**：缺少必要章节（In Scope/Out of Scope、Risks）、Spec 无异常场景、Design 无 Trade-off
- **警告**：模糊用语、Scenario 缺少 GIVEN、字段表未对齐、术语不一致
- **建议**：格式优化、分隔符缺失、可以补充的额外场景

**Guardrails**
- 审核前必须读取所有相关工件 + 现有代码中的被引用类型
- 不凭空猜测技术细节，基于代码库实际情况判断
- 报告中的每条问题必须具体可操作（引用章节/行号）
- 生成优化文件时遵循 openspec-docs.mdc 规则中的所有标准
