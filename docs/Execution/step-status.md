# 执行手册 Step 1～Step 11 状态

依据：`D:\LEARN\AI\programs\AgentTask\Projects\municipal-facility-ops\docs\municipal-facility-ops.md`

## Step 1：确认项目范围与验收边界

**状态：完成**。范围、角色、MVP 边界和公开/合成/用户数据边界记录在 `project-scope.md`。

## Step 2：创建项目仓库与基础目录

**状态：完成**。项目目录、Git `main` 分支、README、环境变量示例、忽略文件、版本文件和各模块目录已建立。Docker 部署文件按手册保留占位。

## Step 3：配置本地开发环境

**状态：完成**。指定 Python 虚拟环境已安装锁定依赖，Node/npm 和前端依赖已安装；pytest、Ruff、mypy、Vue 类型检查和 Vite 构建命令已配置。`backend/.env` 已在本地生成且被 Git 忽略，真实密钥未写入仓库。

## Step 4：准备本地基础依赖服务

**状态：部分完成**。

- MySQL 8.4 已启动，`municipal_ops` 数据库和本地用户已创建，连接验证通过。
- Chroma 0.5.23 已以本地进程启动，`/api/v1/heartbeat` 验证通过。
- 当前机器没有可用的 OpenAI-compatible 模型端点，也没有真实 API Key；模型连通性待配置后验证。
- 未编写、构建或启动 Docker Compose。

## Step 5：下载并登记公开数据

**状态：完成**。`data/raw/public` 和 `data/raw/docs` 已包含 NYC 311、路灯/交通信号、NYC DOT 坑洞数据及元数据文档；`data/manifests/manifest.json` 已补充 dataset ID、筛选条件、来源系统、文件大小、行数和 SHA256。当前清单校验结果为 23 个文件、0 个不匹配，原始文件未修改。

## Step 6：生成并登记合成数据

**状态：完成**。已使用 `synthetic-v2` 和固定 seed `20261025` 生成 13 个合成数据文件，覆盖设施、位置、队伍、人员、供应商、SLA、报修、巡检、工单、验收、Agent 运行、审计和知识文档；manifest 已登记 22 个文件并通过 0 不匹配校验。详见 `step06-synthetic-data.md`。

## Step 7：建立数据清洗与统一映射

**状态：完成**。已将 3 个公开 CSV 共 62,000 行统一为 `facility_issue_events.csv`，生成字段、缺失值、重复值、失败行和清洗批次报告；原始文件未覆盖。详见 `step07-data-cleaning.md`。

## Step 1～Step 7 复核

**状态：已按仓库执行手册复核**。复核证据、命令和边界见 `step01-07-review.md`。Step 4 的模型服务未配置状态保留。

## Step 8：设计 MySQL 数据模型

**状态：完成**。已完成 17 张核心表、外键、索引、来源/版本/软删除字段、幂等键、区域字段、Agent 运行关联和审计不可变设计；本地结构验证通过。应用最小权限账号模板已提供，因当前本地账号没有 `CREATE ROLE`/`CREATE USER` 权限，未擅自修改账号授权。详见 `step08-mysql-model.md`。

## Step 9：实现数据库初始化与种子导入

**状态：完成**。已实现可重复的 seed plan、事务导入、批次日志和失败回滚；导入 63,200 条报修/公开事件、500 个设施、1,600 个巡检任务、1,800 个工单、900 条验收、1,200 次 Agent 运行和 1,800 条审计记录。重复导入行数保持不变，外键、状态、时间顺序和幂等校验通过。详见 `step09-seed-import.md`。

## Step 10：搭建 FastAPI 应用基础层

**状态：完成**。已实现应用工厂、配置校验、SQLAlchemy session 和依赖注入、CORS、请求/trace ID、JSON 结构化日志、统一异常响应、OpenAPI 元数据、`/health` 和真实依赖检查 `/ready`。详见 `step10-fastapi.md`。

## Step 11：实现认证与权限控制

**状态：完成**。已实现 HS256 Bearer Token 签发与校验、登录和当前用户接口、角色/菜单/API 权限映射、区域数据范围、路由/服务/工具三层授权、高风险工单关闭人工确认，以及登录、令牌无效、权限拒绝、区域拒绝和人工确认事件 JSONL 记录。认证配置通过 `AUTH_*` 环境变量提供，未配置登录凭据时接口安全地返回 `AUTH_NOT_CONFIGURED`。详见 `step11-auth.md`。

Step 12 尚未开始。
