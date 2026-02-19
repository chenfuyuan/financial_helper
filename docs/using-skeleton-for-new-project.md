# 从骨架创建新项目

本文说明如何将本 DDD + FastAPI 骨架作为**新项目**的起点（拥有独立的 git 历史与远程仓库）。是否需要重新初始化 git，取决于你获取代码的方式。

## 方式一：GitHub 模板仓库（推荐，无需手动 re-init）

1. 在 GitHub 上为本仓库开启 **Template repository**：Settings → General → 勾选 **Template repository**。
2. 创建新项目：在 GitHub 点击 **Use this template** → 创建新仓库（如 `my-new-service`）。
3. 本地：`git clone https://github.com/<you>/my-new-service.git && cd my-new-service`。
4. 按下方「共同后续步骤」完成依赖、`.env`、Docker、迁移、pre-commit 等配置。

新仓库已有独立的 git 历史与 `origin`，**不需要**再删除 `.git` 或执行 `git init`。

## 方式二：Clone 后当新项目用（必须 re-init git）

若通过 clone 本仓库得到代码并希望作为新项目，必须重新初始化 git，使新项目拥有自己的历史和远程（否则会保留骨架的完整历史并指向原仓库的 `origin`）。

1. 克隆骨架（不要 clone 到已有 git 仓库内）：
   ```bash
   git clone <本骨架仓库 URL> my-new-project && cd my-new-project
   ```

2. 去掉原有 git 元数据并新建仓库：
   ```bash
   rm -rf .git
   git init
   git add .
   git commit -m "chore: initial commit from DDD FastAPI skeleton"
   git remote add origin <你的新项目仓库 URL>
   git branch -M main
   git push -u origin main
   ```

3. 可选：更新项目身份（如 `pyproject.toml` 的 `name`、`description`，`README.md` 标题）。

4. 按下方「共同后续步骤」继续。

## 共同后续步骤（两种方式之后）

- 安装依赖：`pip install -e ".[dev]"`
- 环境：`cp .env.example .env`，按需修改
- 服务：`make docker-up`
- 迁移：`make migrate`
- Pre-commit（可选）：`pre-commit install`
- 提交前：运行 `make ci`（lint、format 检查、type-check、架构守护、测试）

完整快速开始与开发命令见 [README.md](../README.md)。
