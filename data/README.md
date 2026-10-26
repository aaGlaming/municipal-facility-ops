# Data layout

```text
raw/public/   官方 CSV、JSON 元数据
raw/docs/     官方维护文档和 Open311 规范
processed/    统一后的 facility_issue_events.csv
synthetic/    内部业务闭环合成数据
manifests/    来源和哈希清单
```

`source_type=public` 表示官方公开数据，`source_type=synthetic` 表示本项目为开发和评测补齐的数据。任何合成记录不得在产品界面中伪装成真实政府业务记录。
