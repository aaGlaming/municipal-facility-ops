# Step 34：完成数据备份与恢复验证

## 备份范围

新增 `scripts/backup_restore.py`，默认将以下内容备份到项目外的 `../backups/municipal-facility-ops/step34`：

- `data/`：公开数据、合成数据、处理结果、manifest、Chroma 持久化文件。
- `evaluation/`：Gold Set、基线配置和评测报告。
- `infra/`：MySQL Schema、安全模板和 Chroma 运行配置。
- `backend/.env.example`、`frontend/.env.example`、`compose.yaml`、`README.md`。

真实 `backend/.env` 和 `frontend/.env` 不进入备份。每个文件记录大小和 SHA256，备份清单写入备份目录 `manifest.json`。

## 恢复验证

脚本会将 payload 复制到独立 `restore-check` 目录，逐文件重新计算 SHA256，并检查关键文件：

- 数据来源 manifest、处理后事件 CSV、合成设施 CSV。
- `data/chroma/chroma.sqlite3`。
- Step29/30/31 评测配置和报告。
- MySQL canonical schema。
- 配置模板。

本次执行结果：63 个文件、59,373,106 bytes，恢复差异 0，关键文件缺失 0，恢复验证通过。

## MySQL 说明

本机 3306 端口没有 MySQL 服务，因此没有生成数据库 dump；报告保留 `mysql.status=unavailable`，并确认 canonical schema、seed 数据和恢复验证材料已纳入备份。待 Step36 Compose 启动 MySQL 后，需补充逻辑 dump、恢复和查询校验。

## 复现命令

```powershell
python scripts/backup_restore.py
pytest -q backend/tests
```

备份报告：`evaluation/reports/step34-backup-restore.json`。

## 校验记录

- 备份与独立恢复：通过。
- SHA256 清单比对：通过。
- `pytest -q backend/tests`：86 passed。
- Ruff 检查和格式检查：通过。
- `git diff --check`：通过。
