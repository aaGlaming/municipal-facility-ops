# Municipal Facility Operations

市政设施巡检与维修平台的数据与工程骨架。项目面向道路、路灯、交通信号、公共设施等问题的发现、分诊、巡检、派工、维修验收和知识问答。

## 数据方案

- `data/raw/public/`：官方公开数据原样保存，包括 NYC 311、NYC DOT 坑洞工单、路灯/交通信号报修数据。
- `data/raw/docs/`：维修规范、Open311 规范和数据元数据，作为 RAG 知识库原始资料。
- `data/processed/`：统一字段后的可导入数据。
- `data/synthetic/`：为补齐内部业务闭环而生成的数据，所有记录带 `source_type=synthetic`。
- `data/manifests/`：来源、下载时间、筛选条件、文件大小和 SHA256。
- `../data/municipal-facility-ops/`：公共备份目录，内容与本项目 `data/` 保持一致。

## 目标技术栈

FastAPI、OpenAI 兼容接口、Chroma、MySQL、LangChain、LangGraph、Vue 3、Element Plus、TypeScript、Docker Compose。

## 目录

```text
backend/       FastAPI、Agent、RAG、工具、数据库访问
frontend/      Vue + Element Plus 前端
scripts/       下载、清洗、合成和校验脚本
data/          原始、处理后、合成和清单数据
docs/          数据来源、数据字典和架构说明
infra/         MySQL 初始化和 Chroma 运行目录
evaluation/    评测数据集和报告
logs/          运行日志
uploads/       文档上传暂存区
```

## 当前交付阶段

Step 1～32 的业务、Agent、RAG、前端、评测和离线验收已完成。Step 33 的真实依赖门禁因本机未运行 MySQL、Chroma 和模型而阻断；Step 34 已完成文件备份与独立恢复，MySQL 逻辑 dump 待 Step 36 Compose 环境补做。交付总览见 `docs/DELIVERY.md`。

## Windows IDE 直启（不使用 Docker）

项目支持在 Windows IDE 中分终端启动 MySQL、Chroma、FastAPI 和 Vue。完整步骤见 [`docs/Execution/windows-direct-start.md`](docs/Execution/windows-direct-start.md)。

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_windows.ps1 -Component mysql
powershell -ExecutionPolicy Bypass -File scripts/start_windows.ps1 -Component chroma
powershell -ExecutionPolicy Bypass -File scripts/start_windows.ps1 -Component backend
powershell -ExecutionPolicy Bypass -File scripts/start_windows.ps1 -Component frontend
```

## 本地运行

后端：

```powershell
$env:PYTHONPATH = "backend"
python -m uvicorn app.main:app --reload --app-dir backend
```

前端：

```powershell
cd frontend
npm ci
npm run type-check
npm run build
npm run dev
```

后端测试：`python -m pytest -q`

Docker Compose 不是 Windows IDE 直启的前置条件；Step 36 仍保留为可选的容器化发布验收。

## 数据准备

```powershell
$py = 'D:\LEARN\AI\programs\AgentTask\env\agent-task\Scripts\python.exe'
& $py scripts\download_public_data.py
& $py scripts\generate_synthetic_data.py
& $py scripts\prepare_data.py
& $py scripts\seed_database.py --data-root data --batch-id step09-20261026
& $py scripts\backup_data.py
```

数据脚本会把来源信息写入 `data/manifests/manifest.json`，并支持将 `data/` 镜像备份到 `D:\LEARN\AI\programs\AgentTask\data\municipal-facility-ops`。原始数据目录不会被清洗脚本覆盖。

## 数据边界

公开数据用于初始化、历史案例和统计分析；正式业务中的报修、派工、验收和审计记录应进入 MySQL。公开数据不等于内部业务事实，合成数据只用于开发、演示和测试。
