# Step 6：生成并登记合成数据

依据：`D:\LEARN\AI\programs\AgentTask\Projects\municipal-facility-ops\docs\municipal-facility-ops.md`

## 状态

**完成**。本步骤未执行 Step 7 及后续步骤。

## 生成配置

- 生成器：`scripts/generate_synthetic_data.py`
- 生成器版本：`synthetic-v2`
- 固定 seed：`20261025`
- 固定生成时间：`2026-01-01T00:00:00Z`
- 输出目录：`data/synthetic`
- 登记清单：`data/manifests/manifest.json`

## 输出规模

| 数据集 | 行数 |
|---|---:|
| `synthetic_facilities.csv` | 500 |
| `synthetic_locations.csv` | 500 |
| `synthetic_teams.csv` | 20 |
| `synthetic_technicians.csv` | 100 |
| `synthetic_vendors.csv` | 40 |
| `synthetic_sla_rules.csv` | 32 |
| `synthetic_citizen_reports.csv` | 1,200 |
| `synthetic_inspection_tasks.csv` | 1,600 |
| `synthetic_work_orders.csv` | 1,800 |
| `synthetic_acceptance_records.csv` | 900 |
| `synthetic_agent_runs.csv` | 1,200 |
| `synthetic_audit_logs.csv` | 1,800 |
| `synthetic_knowledge_docs.jsonl` | 7 |

## 验证结果

- 所有 CSV 和 JSONL 记录均带有 `source_type=synthetic`、生成器版本和生成时间。
- 设施编号唯一；位置、报修、巡检、工单、验收、Agent 运行和审计记录的外键关系已通过测试。
- 相同 seed 和参数重复生成结果一致。
- `verify_manifest` 校验 22 个文件，结果为 0 个不匹配。
- pytest：数据脚本 5 passed；项目全量 9 passed。
- Ruff、Ruff format 和 mypy 检查通过。

Step 7 的公开数据清洗尚未开始。
