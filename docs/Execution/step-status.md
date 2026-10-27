# 执行手册 Step 1～Step 19 状态

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

## Step 12：实现设施与问题上报模块

**状态：完成**。已实现设施分页、筛选、详情、历史事件、地址/坐标/类型/区域查询、附近设施、内部问题上报、公开事件导入、来源区分、外部 ID 去重、幂等提交、重复问题候选检测和状态更新。详见 `step12-facilities-reports.md`。

## Step 13：实现工单与巡检业务模块

**状态：完成**。已实现巡检任务创建、派工、执行、延期和完成；工单创建、分诊、派工、执行、待确认、完成、验收、关闭、拒绝、阻塞、升级、取消和返工；状态机校验、持久化幂等、SLA 截止时间计算、超时升级、处理说明、维修证据和验收材料关联。详见 `step13-work-orders-inspections.md`。

## Step 14：实现 RAG 文档上传与解析

**状态：完成**。已实现 PDF、DOCX、Markdown、TXT、HTML 上传，文件大小/类型/文件名/内容安全校验、SHA256 去重、来源元数据、原始文件保存、段落/标题/页码/表格解析和失败状态记录。详见 `step14-rag-documents.md`。

## Step 15：实现文本清洗与 Chunk 预览

**状态：完成**。已实现不可见字符/重复空白/页眉页脚清洗、标题/段落/表格边界切分、默认 800/120 Chunk 参数、来源和偏移元数据、预览、参数调整和持久化重生成。详见 `step15-text-cleaning-chunks.md`。

## Step 16：实现 Embedding 与 Chroma 入库

**状态：完成**。已实现 OpenAI 兼容 Embedding 批量调用、超时、指数退避重试、限流和文件缓存；已实现 Chroma 写入、文档级重建和删除；已记录模型版本、文档版本和入库批次；失败批次保留可重试状态且不写入不完整向量。详见 `step16-embedding-chroma.md`。实际模型和 Chroma 连通性需配置服务后验证。

## Step 17：实现 RAG 检索与原文展示

**状态：完成**。已实现查询改写和字段提取、区域/设施类型/版本/生效日期过滤、Chroma 向量召回、MySQL 关键词召回、候选去重合并、可选 rerank、默认 Top-K 5、原文片段和 metadata 展示，以及无召回/过期/解析失败/检索服务不可用提示。已提供普通检索和检索调试接口。详见 `step17-rag-retrieval.md`。

## Step 18：设计 Agent 状态与工具契约

**状态：完成**。已定义 LangGraph `AgentState`、请求/计划/观察/证据/错误/停止原因/人工确认/工具调用结构；已登记 16 个命名空间工具的输入输出 schema、Agent 白名单、权限、风险等级、确认策略、幂等规则、审计动作和可重试错误。详见 `step18-agent-contracts.md`。具体工具执行安排在 Step19，Supervisor 循环安排在 Step20。

## Step 19：实现 Agent 工具层

**状态：完成**。已实现统一工具执行网关，接入设施、历史、报修、SLA、巡检、人员/供应商、工单、安全、验收和审计工具；执行前统一校验 schema、Agent 白名单、权限、区域、业务状态、风险确认和幂等键；工具调用写入持久化 `tool_calls` 记录，重复调用返回原结果。详见 `step19-agent-tools.md`。Step20 尚未开始。
