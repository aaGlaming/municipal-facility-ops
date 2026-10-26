# Step 7：建立数据清洗与统一映射

依据：`D:\LEARN\AI\programs\AgentTask\执行手册\V1\municipal-facility-ops.md`

## 状态

**完成**。本步骤未执行 Step 8 及后续步骤。

## 清洗批次

- 批次 ID：`step07-20261026`
- 映射版本：`public-events-v2`
- 输入目录：`data/raw/public`
- 输出目录：`data/processed`
- 输入数据集：3 个公开 CSV，共 62,000 行。
- 输出：`facility_issue_events.csv`，62,000 行。

## 统一规则

- 统一事件编号：以来源文件名和外部 ID 组成 `event_id`；同源重复 ID 使用 `-dup-N` 后缀。
- 统一类别：将路灯、交通信号、道路/坑洞、人行道和树木问题映射为稳定类别值。
- 统一状态：转换为空格分隔的小写下划线形式，例如 `in_progress`。
- 统一时间：支持 ISO 8601、`YYYY/MM/DD HH:MM:SS`、`YYYY-MM-DD HH:MM:SS` 和日期格式，输出 UTC ISO 8601 秒精度。
- 统一行政区：将 `B`、`Q`、`M`、`X`、`S` 等来源缩写映射为标准行政区名称。
- 统一坐标：清洗空值和越界值，保留有效 WGS84 经纬度。
- 记录来源文件、来源行号、映射版本和清洗批次 ID。

## 产物和验证

- `data/processed/facility_issue_events.csv`
- `data/processed/facility_issue_events_summary.json`
- `data/processed/field_statistics.json`
- `data/processed/missing_values.json`
- `data/processed/duplicate_values.json`
- `data/processed/cleaning_failures.jsonl`
- `data/processed/cleaning_batch.json`
- 公开输入文件 SHA256、输出文件 SHA256 和失败值明细已写入清洗批次清单。
- 本批次失败值为 0；缺失值仅保留原始数据中的真实缺失，不用默认值伪造。
- 原始文件哈希未改变，`verify_manifest` 校验通过。
- Step7 测试覆盖跨来源字段映射、日期和坐标清洗、行政区缩写、重复 ID、失败记录和原始文件只读约束。
