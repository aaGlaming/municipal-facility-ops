# Municipal Facility Operations Skeleton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将项目从注释占位骨架补齐为可配置、可启动、可验证并可提交到 GitHub 的最小工程骨架。

**Architecture:** FastAPI 提供健康检查、基础设施状态和最小业务读写接口；Vue/Vite 提供可构建的工作台壳；数据脚本保持来源可追溯和幂等；MySQL schema 与 Compose 对齐需求；Agent/RAG 领域模块保留清晰接口，后续继续实现。

**Tech Stack:** Python 3.11+, FastAPI, Pydantic Settings, SQLAlchemy, PyMySQL, Vue 3, Vite, TypeScript, Docker Compose, pytest.

**Spec:** `D:/LEARN/AI/programs/AgentTask/需求分析/V3/01-市政设施巡检与维修平台.md` and `D:/LEARN/AI/programs/AgentTask/执行手册/V1/municipal-facility-ops.md`

## Global Constraints

- 错误响应包含 `code`、`message`、`trace_id`、`retryable`。
- 默认运行控制为最多 8 次模型调用、16 次工具调用、90 秒超时。
- 公开、合成和用户数据必须可区分。
- 原始数据不可覆盖，数据脚本需要可重复运行。
- 真实密钥不得提交。

## Review Focus

- 启动时缺少环境变量时，应用仍能返回结构化配置错误。
- 数据脚本重复执行时，不应破坏已有 raw 数据或产生不可追溯结果。
- 高风险工单写操作暂不自动执行，接口必须保留人工确认边界。
- Compose 中 MySQL/Chroma 不可用时，健康检查需明确区分存活与就绪。
- 前端必须在没有后端时仍能完成静态构建。

### Task 1: 工程配置和版本基线

**Files:** `pyproject.toml`, `backend/requirements.txt`, `backend/.env.example`, `frontend/package.json`, `README.md`, `.gitignore`

- [ ] 统一依赖和环境变量命名。
- [ ] 写配置校验测试并运行验证。
- [ ] 补充启动和开发命令。

### Task 2: FastAPI 最小可运行后端

**Files:** `backend/app/core/config.py`, `backend/app/schemas/common.py`, `backend/app/main.py`, `backend/app/api/routes/health.py`, `backend/app/api/routes/facilities.py`, `backend/app/api/routes/work_orders.py`, `backend/tests/test_api.py`

- [ ] 先写失败测试：`/health`、`/ready`、结构化错误和工单状态校验。
- [ ] 实现最小 API 和内存数据适配。
- [ ] 运行完整后端测试。

### Task 3: 数据脚本和 MySQL schema

**Files:** `scripts/*.py`, `infra/mysql/init/001_schema.sql`, `backend/tests/test_data_scripts.py`

- [ ] 先写失败测试：备份哈希、合成数据来源标识、统一事件输出。
- [ ] 实现幂等、可追溯的数据脚本。
- [ ] 补齐核心表、状态和幂等索引。

### Task 4: 前端和 Compose

**Files:** `frontend/src/*`, `frontend/package.json`, `frontend/vite.config.ts`, `frontend/index.html`, `compose.yaml`, `backend/Dockerfile`, `frontend/Dockerfile`

- [ ] 补齐 Vue 应用入口、菜单、路由和 API 客户端。
- [ ] 提供可构建的前后端容器配置。
- [ ] 运行前端构建和 Compose 配置检查。

### Task 5: 文档、验证、提交和推送

- [ ] 更新项目状态、运行命令和已知边界。
- [ ] 运行后端测试、数据脚本校验、前端构建和 Git diff 检查。
- [ ] 初始化 Git，添加远程仓库，提交 `项目骨架提交` 并推送。

## 后续执行计划

本计划只覆盖项目骨架和 Step 1～Step 5。执行手册 Step 6～Step 36 的增强计划、Skill 和 MCP 映射见 [`docs/Execution/step06-36-plan.md`](../../Execution/step06-36-plan.md)。
