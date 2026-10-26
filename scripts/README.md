# Data scripts

脚本已提供可复用实现，支持公开数据登记、固定 seed 的合成数据、统一事件清洗和 SHA256 备份校验。

后续实现方向：

- `download_public_data.py`：从官方公开入口下载原始数据和元数据，并生成来源清单。
- `generate_synthetic_data.py`：按固定随机种子生成设施、位置、队伍、人员、供应商、SLA、报修、巡检、工单、验收、Agent 运行、审计和知识文档数据，并更新合成数据 manifest。
- `prepare_data.py`：把不同来源的公开数据统一为 `facility_issue_events.csv`，标准化类别、状态、日期、行政区和坐标，并生成字段统计、缺失值、重复值、失败值和清洗批次报告。
- `backup_data.py`：将项目 `data/` 按原目录复制到 `D:\LEARN\AI\programs\AgentTask\data\municipal-facility-ops` 并逐文件校验 SHA256。

实现时要保持数据处理幂等、来源可追溯、原始数据不可变，并将错误写入运行日志。

执行 Step 6 的默认命令：

```powershell
python scripts/generate_synthetic_data.py --output-dir data/synthetic --manifest data/manifests/manifest.json --seed 20261025
```

执行 Step 7 的默认命令：

```powershell
python scripts/prepare_data.py --input-dir data/raw/public --output-dir data/processed --manifest data/manifests/manifest.json --batch-id step07-20261026
```

验证 Step 8 本地数据库结构：

```powershell
python scripts/verify_schema.py --url $env:MYSQL_URL --allow-missing-audit-triggers
```

完整 schema 和权限边界见 `infra/mysql/init/001_schema.sql` 与 `infra/mysql/security/`。数据库种子导入属于 Step 9。
