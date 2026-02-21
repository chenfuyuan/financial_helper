## Why

当前题材同步采用增量同步策略，通过比较远程和本地数据的哈希值来确定变更。这种方式虽然高效，但在某些情况下可能导致数据不一致或复杂的状态管理。用户需要一种更简单、更可靠的全量同步方式，确保每次同步后本地数据与远程数据完全一致，同时避免删除再重建带来的性能开销和事务复杂性。

## What Changes

- 修改题材同步逻辑为全量同步模式
- 保持现有数据表结构，不采用删除再插入的方式
- 通过批量更新和插入实现全量数据同步
- 优化事务处理，减少提交次数
- 保持现有的错误处理和日志记录机制

## Capabilities

### New Capabilities
- `theme-full-sync`: 全量题材同步能力，通过批量操作实现数据一致性

### Modified Capabilities
- `concept-sync`: 修改现有概念同步的需求，从增量同步改为全量同步模式，但保持数据完整性

## Impact

- **Application Layer**: 修改 `SyncConceptsHandler` 的同步逻辑
- **Domain Layer**: 可能需要调整 `ConceptRepository` 和 `ConceptStockRepository` 的批量操作方法
- **Infrastructure Layer**: 可能需要优化数据库批量操作的性能
- **API Layer**: 同步接口保持不变，但内部行为改变
- **Performance**: 全量同步可能增加数据传输量，但通过批量操作优化写入性能
