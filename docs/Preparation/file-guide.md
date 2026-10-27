# 文件与交付指南

项目已完成 Step 1～35 的业务实现、评测和文档整理；Step 36 负责 Compose 部署和最终发布验收。

| 路径 | 用途 |
|---|---|
| `backend/app/main.py` | FastAPI 应用工厂和统一异常处理 |
| `backend/app/api/routes/` | 健康、认证、设施、报修、巡检、工单、Agent、RAG、监控 API |
| `backend/app/tools/` | Agent 工具契约、白名单和受控执行网关 |
| `backend/app/rag/`、`backend/app/services/` | 文档解析、切块、Embedding、检索和业务服务 |
| `frontend/src/` | Vue 路由、菜单、Agent 工作台、工单、RAG 和监控页面 |
| `data/raw/` | 原始公开资料，只读，不由清洗脚本覆盖 |
| `data/processed/` | 字段映射、事件统一和质量报告 |
| `data/synthetic/` | 固定 seed 的开发/测试数据，记录来源和生成版本 |
| `data/manifests/` | 来源、批次、行数、大小和 SHA256 清单 |
| `evaluation/` | Gold Set、基准配置和可重复评测报告 |
| `infra/mysql/init/` | 按编号执行的 schema 迁移脚本 |
| `.env.example` | 只放变量名和开发示例，不放真实密钥 |

`.env`、上传文件、Embedding 缓存、Chroma 运行数据、日志、pytest/Ruff/mypy 缓存和前端构建产物不进入 Git。提交前执行 `git status --short` 和 `git diff --check`；备份使用 `python scripts/backup_restore.py`，不要手工复制生产密钥。

修改 API、配置、数据来源或运行命令时，同时更新 `docs/Preparation/`、对应 `docs/Execution/step*.md` 和 [`docs/DELIVERY.md`](../DELIVERY.md)。
