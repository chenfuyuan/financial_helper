---
description: 项目开发 SOP 工作流
globs:
---

# 开发 SOP（标准作业流程）

## 核心原则

- **TDD**：先写失败测试 → 最小实现 → 通过 → 重构
- **频繁提交**：每个有意义的变更都 commit
- **先设计后编码**：新功能/模块 必须先通过 brainstorming → writing-plans 流程

## 分支策略

| 场景 | 分支命名 | 基线 |
|------|---------|------|
| 新功能 | `feature/<name>` | main |
| 修复 | `fix/<name>` | main |
| 重构 | `refactor/<name>` | main |

在 `.worktrees/` 下创建隔离工作区，不在 main 上直接开发。

## 新功能/新模块的开发流程

```
1. brainstorming        → 探索 → 提问 → 方案选型 → 设计文档
2. writing-plans        → 设计文档 → 分步实施计划
3. using-git-worktrees  → 创建隔离工作区
4. executing-plans      → 分批执行（每批 3 任务）→ 检查点 → 反馈
5. verification         → 运行 pytest + ruff + mypy
6. finishing-branch     → 合并/PR/清理
```

## 新建业务模块的 Checklist

```
modules/<name>/
├── domain/
│   ├── <entity>.py              # 聚合根/实体
│   ├── <event>.py               # 领域事件
│   └── <entity>_repository.py   # 仓储接口
├── application/
│   ├── commands/
│   │   ├── <action>.py          # Command
│   │   └── <action>_handler.py  # Handler
│   └── queries/
│       ├── <query>.py           # Query
│       └── <query>_handler.py   # Handler
├── infrastructure/
│   ├── models/<entity>_model.py # SQLAlchemy Model
│   └── sqlalchemy_<entity>_repository.py
└── interfaces/api/
    ├── <entity>_router.py       # FastAPI Router
    ├── requests/                 # Pydantic 请求模型
    └── responses/                # Pydantic 响应模型
```

完成后：
1. 在 `main.py:_register_handlers()` 注册 handler
2. 在 `main.py` 中 `app.include_router()`
3. 在 `migrations/env.py` import model（Alembic 自动发现）
4. 写单元测试（domain）+ 集成测试（handler + API）

## 常用命令

```bash
make dev             # 启动开发服务器
make test            # pytest tests/ -v
make lint            # ruff check src/ tests/
make format          # ruff format + fix
make type-check      # mypy src/
make migrate         # alembic upgrade head
make migrate-create msg="描述"  # 创建新迁移
make docker-up       # 启动 Docker 服务
```

## 验证清单（提交/合并前）

1. `make test` — 所有测试通过
2. `make lint` — 无 lint 错误
3. `make type-check` — 无类型错误
4. 无硬编码密钥、密码、连接字符串
5. 新代码有对应测试
