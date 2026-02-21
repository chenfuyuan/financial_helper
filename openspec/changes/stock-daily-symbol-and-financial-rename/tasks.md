## 1. 数据库迁移脚本

- [x] 1.1 创建为 stock_daily 表添加 symbol 字段的 Alembic 迁移脚本
- [x] 1.2 创建重命名 financial_indicator 为 stock_financial 并添加 symbol 字段的 Alembic 迁移脚本
- [x] 1.3 为 stock_daily 表的 symbol 字段添加从 stock_basic 表填充数据的逻辑
- [ ] 1.4 测试迁移脚本的升级和降级功能

## 2. StockDaily 实体和映射器更新

- [x] 2.1 更新 StockDaily 实体类添加 symbol 字段
- [x] 2.2 更新 StockDailyPersistenceMapper 支持 symbol 字段映射
- [x] 2.3 更新 stock_daily 相关的 ORM 模型

## 3. StockFinancial 重命名和更新

- [x] 3.1 重命名 financial_indicator.py 为 stock_financial.py
- [x] 3.2 更新实体类名从 FinancialIndicator 为 StockFinancial
- [x] 3.3 在 StockFinancial 实体中添加 symbol 字段
- [x] 3.4 重命名 financial_indicator_persistence_mapper.py 为 stock_financial_persistence_mapper.py
- [x] 3.5 更新映射器类名和支持 symbol 字段
- [x] 3.6 重命名 financial_indicator_repository.py 为 stock_financial_repository.py
- [x] 3.7 更新仓储类名和接口

## 4. 应用层和服务更新

- [x] 4.1 更新所有导入语句引用新的文件名和类名
- [x] 4.2 更新财务指标相关的处理器文件名和类名
- [x] 4.3 更新应用层服务中的引用
- [x] 4.4 更新 API 控制器中的引用

## 5. 测试更新

- [x] 5.1 更新所有相关的单元测试文件名和引用
- [x] 5.2 更新集成测试中的表名和字段引用
- [x] 5.3 更新测试数据和断言以支持新的 symbol 字段
- [x] 5.4 运行完整测试套件验证功能正常

## 6. 验证和清理

- [x] 6.1 执行数据库迁移脚本验证变更
- [x] 6.2 验证所有 API 端点功能正常
- [x] 6.3 检查代码中是否还有遗漏的旧引用
- [x] 6.4 更新相关文档和注释
