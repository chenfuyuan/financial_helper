---
name: pre-commit-verify
description: >-
  提交代码前的验证清单。当准备 commit、完成功能实现、或用户说"提交"、
  "commit"、"push"、"检查一下"时使用。
---

# 提交前验证

代码提交前**必须**按顺序完成以下检查，任何一步失败则停止并修复。

## 验证清单

```
- [ ] 1. 格式化与静态检查
- [ ] 2. 架构守护
- [ ] 3. 单元测试
- [ ] 4. 全量 CI
```

## 步骤

### 1. 格式化与静态检查

```bash
make lint
```

修复所有 linter 报错后再继续。

### 2. 架构守护

```bash
make architecture
```

验证 import-linter 层依赖 + `tests/architecture/` 检查通过。

### 3. 单元测试

```bash
python -m pytest tests/unit/ -v --tb=short
```

全部通过后继续。

### 4. 全量 CI

```bash
make ci
```

这是最终关卡，包含格式化、架构守护、全量测试。**只有 `make ci` 通过后才能 commit。**

## 失败处理

- 如果任何步骤失败，**立即停止**并修复问题
- 修复后从失败的步骤重新开始验证
- 不要跳过任何步骤

## 提交

全部通过后：

```bash
git add <changed_files>
git commit -m "<commit_message>"
```

遵循项目的 commit message 风格（查看 `git log --oneline -10` 获取参考）。
