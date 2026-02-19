# 新模块脚手架

从 `data_engineering` 模块复制并重命名，快速生成新的限界上下文模块（含 domain / application / infrastructure / interfaces 与对应测试）。

---

## AI 编程使用指南

### 创建金融助手系统新模块前
请先阅读：
1. **docs/plans/financial-helper/README.md** - 设计文档总索引
2. **docs/plans/financial-helper/02-dependencies.md** - 模块边界约束
3. **docs/plans/financial-helper/modules/*.md** - 参考现有模块设计

### 金融助手系统现有模块
本项目已有 9 个业务模块，无需重复创建：
- foundation - 基础设施层
- data_engineering - 数据工程层
- llm_gateway - LLM 网关层
- knowledge_center - 知识中心
- market_insight - 市场洞察
- coordinator - 协调器
- research - 研究模块
- debate - 辩论模块
- judge - 决策模块

如需实现以上模块，请参考对应的设计文档，不要使用脚手架重新创建。

## 用法

```bash
# 模块名用小写、连字符/下划线，聚合名默认为首字母大写的模块名
make new-module name=product

# 或直接调用脚本，可选指定聚合名
python scripts/new_module.py product
python scripts/new_module.py order --aggregate Order
```

- **name**：模块目录名，即 `src/app/modules/<name>`、`tests/unit/modules/<name>`、`tests/api/modules/<name>`。
- **--aggregate**：可选。聚合根类名（PascalCase），默认由模块名推导（如 `product` → `Product`）。

生成内容为 data_engineering 的完整拷贝，并做以下替换：

| 原样 | 替换为 |
|------|--------|
| `data_engineering`（模块路径） | `<name>` |
| `StockBasic` | 聚合名（如 `Product`） |
| `stock_basic` | 聚合名小写+下划线（如 `product`） |
| `StockBasicModel` / `stock_basic_model` | 聚合名+Model / 聚合名小写+_model |

## 脚手架完成后必做

1. **注册路由与 Handler（main）**  
   在 `app/interfaces/main.py` 中：
   - `from app.modules.<name>.interfaces.api.<aggregate_slug>_router import router as <name>_router`
   - 在 `_register_handlers` 中注册新模块的 Command/Query Handler
   - `app.include_router(<name>_router, prefix="/api/v1")`

2. **注册 Handler（API 测试）**  
   在 `tests/api/conftest.py` 的 `_register_handlers` 中：
   - import 新模块的 Command、Query、Handler、Repository
   - 为 mediator 注册 `register_command_handler` / `register_query_handler`
   - 若有新 Model，在 `import app.modules.<name>.infrastructure.models` 中一并引入

3. **按业务调整**
   - 聚合根字段、值对象、领域事件
   - 表名（`__tablename__`）、路由前缀（router `prefix`）、URL 路径
   - 若复数不规则（如 category → categories），改表名与路由为实际复数

4. **数据库迁移**
   ```bash
   make migrate-create msg="add <name> tables"
   make migrate
   ```

## 验证

```bash
make test && make lint && make type-check
```

新模块的单元测试、接口测试会随全量测试一起运行。
