# Windows IDE 直启指南（不使用 Docker）

本项目支持在 Windows IDE 中分别启动后端、前端、MySQL 和 Chroma，不要求 Docker。前后端启动脚本不会自动修改数据库或导入种子。

## 一次性准备

1. 安装 Python 3.11+、Node.js/npm、MySQL 8.4。
2. 在 MySQL 中创建数据库和用户，或按 `infra/mysql/init/001_schema.sql` 初始化：

   `municipal_ops`、用户 `municipal`、密码 `municipal_dev`，监听 `127.0.0.1:3306`。
3. 安装后端依赖和前端依赖：

   `$env:PYTHONPATH='backend'; python -m pip install -r backend/requirements-dev.txt`

   `npm --prefix frontend ci`

   如果 IDE 没有自动激活项目虚拟环境，请先在 IDE 终端选择包含 `chromadb` 的 Python 解释器；脚本会优先使用 PATH 中的 `chroma`，否则回退到 `python -m chromadb.cli.cli`。
4. 首次运行会从示例创建 `backend/.env` 和 `frontend/.env`；生产或共享环境必须替换 `AUTH_SECRET`、登录凭据和模型配置。

## IDE 终端启动

在仓库根目录打开四个终端：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_windows.ps1 -Component mysql
powershell -ExecutionPolicy Bypass -File scripts/start_windows.ps1 -Component chroma
powershell -ExecutionPolicy Bypass -File scripts/start_windows.ps1 -Component backend
powershell -ExecutionPolicy Bypass -File scripts/start_windows.ps1 -Component frontend
```

也可以直接运行：

```powershell
$env:PYTHONPATH = 'backend'
python -m uvicorn app.main:app --reload --app-dir backend --host 127.0.0.1 --port 8000
npm --prefix frontend run dev -- --host 127.0.0.1 --port 5173
chroma run --path .chroma --host 127.0.0.1 --port 8001
```

前端地址为 `http://127.0.0.1:5173/login`，后端文档为 `http://127.0.0.1:8000/docs`。

## 初始化和检查

```powershell
python scripts/verify_schema.py --url $env:MYSQL_URL --allow-missing-audit-triggers
python scripts/seed_database.py --data-root data --batch-id step09-windows --dry-run
python scripts/final_local_acceptance.py
```

`/health` 只检查 FastAPI 进程；`/ready` 只有在 MySQL、Chroma 和模型均可访问时才返回 200。没有配置 LLM 时，前端壳和确定性业务测试仍可启动，但 Agent 模型调用和真实 Embedding 不可用。

## 停止

在各终端按 Ctrl+C；MySQL 服务可执行：

`Stop-Service MySQL84`
