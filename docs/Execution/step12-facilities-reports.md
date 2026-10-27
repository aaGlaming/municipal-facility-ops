# Step 12：设施与问题上报模块

## 已实现能力

- 设施列表支持分页、`type`、状态、区域、来源和地址/编号关键词筛选。
- 设施详情返回位置、来源、状态和维护属性；设施历史事件通过关联问题上报查询。
- 附近设施使用 WGS84 坐标和 Haversine 距离计算，支持半径、类型、区域权限和分页。
- `POST /api/reports` 创建内部问题上报，保存原始描述、结构化分类、位置、来源和幂等键。
- `GET /api/reports` 和 `GET /api/reports/{report_id}` 查询问题，`PATCH /status` 执行状态流转。
- `POST /api/reports/import/public` 导入公开事件，强制写入 `source_type=public`；内部报修写入 `source_type=internal`。
- 外部 ID 按来源系统去重；幂等键重复提交返回已有记录；相同设施、分类和描述在 24 小时内会返回 `duplicate_of` 候选关联。
- 设施和问题查询均执行令牌权限及区域范围校验。

## 数据和接口边界

设施、位置和问题上报分别对应 `facilities`、`locations` 和 `citizen_reports` 表。公开导入不能覆盖内部来源字段，原始 `description` 保留原始文本，`category`、`subcategory`、坐标和区域作为结构化字段单独保存。

## 验证结果

- `python -m pytest -q`：28 passed
- `python -m ruff check backend scripts`：通过
- `python -m ruff format --check backend scripts`：通过

Step 13 尚未开始。
