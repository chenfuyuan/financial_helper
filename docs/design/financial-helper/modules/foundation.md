# FOUNDATION（基础设施层）

**日期：** 2026-02-19
**作者：** financial_helper 团队

---

## 3.1 FOUNDATION（基础设施层）

**职责：** 提供所有上层模块共享的基础技术能力，不包含任何业务逻辑。

**子模块：**
- `task_scheduler` - 任务调度器（Celery Beat）
- `crawler` - 爬虫引擎（Scrapy/Playwright）
- `search_engine` - 搜索引擎（Elasticsearch）
- `notification` - 通知服务（邮件、企业微信、钉钉）
- `cache` - 缓存服务（Redis）
- `storage` - 存储服务（文件、对象存储）

**暴露接口：**
- `TaskScheduler.schedule(task) -> task_id`
- `Crawler.crawl(config) -> result_stream`
- `SearchEngine.search(query) -> results`
- `Notification.send(channel, message) -> status`
- `Cache.get/set/delete(key) -> value`

**依赖：** 无（最底层）

**被依赖：** 所有业务模块

**禁止：**
- ✗ 直接访问业务数据库
- ✗ 包含业务逻辑（如股票分析规则）
- ✗ 调用上层模块
