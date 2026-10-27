# 数据与交付脚本

脚本均可从仓库根目录执行，默认使用本地文件和固定参数，不依赖外部 MCP。

- `download_public_data.py`：下载并登记公开原始数据和元数据。
- `generate_synthetic_data.py`：固定 seed 生成设施、人员、SLA、报修、巡检、工单、验收、Agent 和审计数据。
- `prepare_data.py`：将公开事件统一到 `data/processed/` 并生成质量报告。
- `verify_schema.py`：检查 MySQL 表、字段、索引、外键和审计触发器。
- `seed_database.py`：批次化、事务化导入种子；`--dry-run` 只校验。
- `evaluate_benchmark.py`、`evaluate_rag.py`、`evaluate_agent_security.py`：执行统一基线、RAG 和安全评测。
- `final_local_acceptance.py`：检查本地 `/health`、`/ready` 和前端壳。
- `backup_data.py`：复制并校验 `data/` 镜像。
- `backup_restore.py`：生成 SHA256 清单并独立恢复验证。

实现时要保持数据处理幂等、来源可追溯、原始数据不可变，并将错误写入运行日志。

## 常用命令

```powershell
python scripts/generate_synthetic_data.py --output-dir data/synthetic --manifest data/manifests/manifest.json --seed 20261025
```

```powershell
python scripts/generate_synthetic_data.py --output-dir data/synthetic --manifest data/manifests/manifest.json --seed 20261025
python scripts/prepare_data.py --input-dir data/raw/public --output-dir data/processed --manifest data/manifests/manifest.json --batch-id step07-20261026
python scripts/seed_database.py --data-root data --batch-id step09-20261026 --dry-run
python scripts/backup_restore.py
```

运行需要导入应用模块的评测脚本前设置 `$env:PYTHONPATH='backend'`。原始数据不覆盖，真实 `.env` 不会被备份。
