# 统一数据字典

## facility_issue_events.csv

| 字段 | 含义 |
|---|---|
| `event_id` | 统一事件编号 |
| `source_dataset` | 原始来源数据集 |
| `source_type` | `public` 或 `synthetic` |
| `category` | 设施问题大类 |
| `subcategory` | 来源问题子类 |
| `description` | 问题描述和处理说明 |
| `status` | 来源状态 |
| `created_at` / `closed_at` | 创建和关闭时间 |
| `agency` | 负责机构 |
| `address` / `borough` | 地址和行政区 |
| `latitude` / `longitude` | WGS84 坐标 |
| `external_id` | 来源系统编号 |

## 合成业务表

- `synthetic_facilities.csv`：设施台账。
- `synthetic_citizen_reports.csv`：演示用报修。
- `synthetic_inspection_tasks.csv`：巡检任务和结果。
- `synthetic_work_orders.csv`：工单、派工、SLA 和幂等键。
- `synthetic_vendors.csv`、`synthetic_technicians.csv`：供应商和人员能力。
- `synthetic_acceptance_records.csv`：维修验收。
- `synthetic_agent_runs.csv`、`synthetic_audit_logs.csv`：运行轨迹和审计。
- `synthetic_knowledge_docs.jsonl`：仅用于演示的维修规则文档。
