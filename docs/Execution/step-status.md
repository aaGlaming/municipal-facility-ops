# 执行手册 Step 1～Step 5 状态

依据：`D:\LEARN\AI\programs\AgentTask\执行手册\V1\municipal-facility-ops.md`

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

**状态：完成**。`data/raw/public` 和 `data/raw/docs` 已包含 NYC 311、路灯/交通信号、NYC DOT 坑洞数据及元数据文档；`data/manifests/manifest.json` 已补充 dataset ID、筛选条件、来源系统、文件大小、行数和 SHA256。清单校验结果为 20 个文件、0 个不匹配，原始文件未修改。
