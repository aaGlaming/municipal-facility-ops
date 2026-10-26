# 本地环境记录

## 指定运行环境

- Python：`D:\LEARN\AI\programs\AgentTask\env\agent-task\Scripts\python.exe`
- Node.js/npm：已安装，前端依赖通过 `npm ci` 安装。
- MySQL：本机 MySQL 8.4，使用 `127.0.0.1:3306`。
- Chroma：本机 Chroma 0.5.23，使用 `127.0.0.1:8001`。

## 配置

复制 `backend/.env.example` 为 `backend/.env`，填写本机数据库、Chroma 和模型服务配置。真实 API Key 只保存在本地 `.env`，不提交 Git。

## 检查命令

```powershell
$py = 'D:\LEARN\AI\programs\AgentTask\env\agent-task\Scripts\python.exe'
& $py -m pytest -q
& $py -m ruff check backend scripts
& $py -m ruff format --check backend scripts
& $py -m mypy backend/app scripts
cd frontend
npm run type-check
npm run build
```

当前没有可用的本地 OpenAI-compatible 模型端点或真实 API Key，因此模型连通性只能在配置端点后验证。
