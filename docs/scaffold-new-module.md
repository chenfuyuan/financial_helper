# 新模块脚手架

从 `example` 模块复制并重命名，快速生成新的限界上下文模块（含 domain / application / infrastructure / interfaces 与对应测试）。

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

生成内容为 example 的完整拷贝，并做以下替换：

| 原样 | 替换为 |
|------|--------|
| `example`（模块路径） | `<name>` |
| `Note` | 聚合名（如 `Product`） |
| `note` | 聚合名小写（如 `product`） |
| `notes`（表名/路由前缀） | `<name>s`（如 `products`） |

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
