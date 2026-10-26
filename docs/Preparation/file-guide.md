# 文件说明指南

项目骨架已经具备最小可运行入口。Agent、RAG 和完整业务持久化仍按执行手册逐步实现。

| 文件 | 后续应补充 |
|---|---|
| `frontend/package.json` | 锁定 Vue、Element Plus、Axios、Router、TypeScript 版本和 build/type-check scripts |
| `frontend/tsconfig.json` | 路径别名、Vue 类型支持、严格类型检查和构建范围 |
| `data/manifests/manifest.json` | 每个数据文件的来源 URL、筛选条件、下载时间、行数、大小和 SHA256 |
| `data/processed/*.json` | 清洗批次、字段统计、缺失值和重复值报告 |
| `.env.example` | 只放变量名和开发示例，不放真实 API Key |

实现后续功能时要按照本指南和各模块职责逐个补齐，不要把业务逻辑堆到入口文件中。
