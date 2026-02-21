## Context

当前系统中，stock_daily 和 financial_indicator 表使用 third_code 作为股票标识符。为了提高数据标准化和与行业惯例保持一致，需要：

1. 在 stock_daily 表中新增 symbol 字段
2. 将 financial_indicator 表重命名为 stock_financial 并新增 symbol 字段
3. 更新所有相关的代码文件名和引用

当前状态：
- stock_daily 表结构包含 source, third_code 等字段
- financial_indicator 相关的文件分布在多个模块中
- 现有的同步逻辑依赖于当前的表结构

约束条件：
- 需要保持数据迁移的向后兼容性
- 不能影响现有的 API 接口行为
- 必须更新所有相关的测试用例

## Goals / Non-Goals

**Goals:**
- 为 stock_daily 表新增 symbol 字段支持
- 将 financial_indicator 重命名为 stock_financial 并新增 symbol 字段
- 更新所有相关的实体类、映射器、仓储等代码
- 提供数据库迁移脚本
- 确保现有功能不受影响

**Non-Goals:**
- 修改 API 接口契约
- 改变业务逻辑行为
- 修改其他不相关的表结构

## Decisions

### 数据库字段位置决策
在 third_code 后面添加 symbol 字段，保持表结构的一致性和可读性。

### 表重命名策略
使用 Alembic 迁移脚本进行表重命名，确保数据的完整性和可回滚性。

### 文件重命名策略
- 实体类：financial_indicator.py → stock_financial.py
- 映射器：financial_indicator_persistence_mapper.py → stock_financial_persistence_mapper.py
- 仓储：financial_indicator_repository.py → stock_financial_repository.py
- 处理器：financial_indicator_handler.py → stock_financial_handler.py

### 迁移策略
1. 先添加新字段（symbol）
2. 从 stock_basic 表填充 symbol 字段数据
3. 再进行表重命名
4. 最后更新代码引用
5. 每个步骤都有独立的迁移脚本

### Symbol 字段填充逻辑
- stock_daily 表的 symbol 字段通过 source 和 third_code 字段与 stock_basic 表关联
- 使用 SQL UPDATE 语句从 stock_basic 表获取对应的 symbol 值
- 填充逻辑：`UPDATE stock_daily SET symbol = (SELECT sb.symbol FROM stock_basic sb WHERE sb.source = stock_daily.source AND sb.third_code = stock_daily.third_code)`

## Risks / Trade-offs

**[Risk]** 数据迁移过程中可能出现数据丢失 → **Mitigation**: 使用事务性迁移脚本，包含回滚测试

**[Risk]** 现有代码引用路径可能遗漏 → **Mitigation**: 使用全局搜索替换，并运行完整测试套件

**[Risk]** API 兼容性问题 → **Mitigation**: 保持对外接口不变，仅修改内部实现

**[Trade-off]** 文件重命名可能导致 Git 历史追踪困难 → **Accept**: 使用 git mv 保持历史记录

## Migration Plan

### 阶段 1: 数据库结构变更
1. 创建 Alembic 迁移脚本为 stock_daily 添加 symbol 字段
2. 创建 Alembic 迁移脚本重命名 financial_indicator 为 stock_financial 并添加 symbol 字段

### 阶段 2: 代码文件重命名
1. 重命名实体类文件
2. 重命名映射器文件  
3. 重命名仓储文件
4. 重命名处理器文件

### 阶段 3: 代码内容更新
1. 更新所有 import 语句
2. 更新实体类定义
3. 更新映射器逻辑
4. 更新仓储实现
5. 更新应用层服务

### 阶段 4: 测试和验证
1. 运行数据库迁移
2. 执行完整测试套件
3. 验证 API 功能正常

### 回滚策略
每个迁移脚本都包含对应的 downgrade 方法，支持快速回滚到变更前状态。

## Open Questions

- ~~symbol 字段的数据来源和填充逻辑~~ - 已解决：从 stock_basic 表通过 source 和 third_code 关联获取
- ~~是否需要为现有数据填充 symbol 字段~~ - 已解决：需要在迁移脚本中填充现有数据
- 迁移过程中的停机时间要求
