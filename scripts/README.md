# Data scripts

脚本已提供可复用实现，支持公开数据登记、固定 seed 的合成数据、统一事件清洗和 SHA256 备份校验。

后续实现方向：

- `download_public_data.py`：从官方公开入口下载原始数据和元数据，并生成来源清单。
- `generate_synthetic_data.py`：按固定随机种子生成设施、位置、队伍、人员、供应商、SLA、报修、巡检、工单、验收、Agent 运行、审计和知识文档数据，并更新合成数据 manifest。
- `prepare_data.py`：把不同来源的公开数据统一为 `facility_issue_events.csv`，同时生成字段统计。
- `backup_data.py`：将项目 `data/` 按原目录复制到 `D:\LEARN\AI\programs\AgentTask\data\municipal-facility-ops` 并逐文件校验 SHA256。

实现时要保持数据处理幂等、来源可追溯、原始数据不可变，并将错误写入运行日志。

执行 Step 6 的默认命令：

```powershell
python scripts/generate_synthetic_data.py --output-dir data/synthetic --manifest data/manifests/manifest.json --seed 20261025
```
