# 数据来源

## 公开数据

| 文件 | 来源 | 形式 | 用途 |
|---|---|---|---|
| `nyc_311_relevant.csv` | NYC Open Data 311 | Socrata CSV/API | 问题上报、问题类型、部门、位置和状态 |
| `nyc_streetlight_traffic_signal_311.csv` | NYC Open Data | Socrata CSV/API | 路灯和交通信号专项问题 |
| `nyc_pothole_work_orders_closed.csv` | NYC DOT | CSV | 坑洞维修历史、报告时间和关闭时间 |
| `nyc_*_metadata.json` | NYC Open Data API | JSON | 字段定义和来源元数据 |
| `street_potholes_metadata.pdf` | NYC DOT | PDF | 坑洞工单口径与元数据 |
| `open311_georeport_v2.md` | Open311 | Markdown | 服务请求接口与字段参考 |

## 下载策略

- 311 和路灯数据取最近时间窗口内、与市政设施相关的记录，避免把整库下载变成不可复现的超大文件。
- 坑洞工单保留官方 CSV 下载结果或受控条数样本，保留 `download_url`、`retrieved_at` 和 SHA256。
- 公开数据不会被改写；清洗结果只放在 `data/processed/`。

## 合成数据

公开数据没有完整覆盖内部设施台账、巡检计划、人员技能、供应商、备件、SLA、验收和审计，所以这些表在 `data/synthetic/` 中按固定随机种子生成。合成记录带有 `source_type=synthetic`、`generator_version` 和 `generated_at`。
