# 执行手册 Step 6～Step 36 增强实施计划

> 本计划以仓库内 `docs/municipal-facility-ops.md` 为执行顺序，以需求分析文档为业务验收依据。Step 1～Step 5 的记录见当前目录下的执行记录文档。

## 使用原则

- 每个 Step 完成前先写可重复的验证或评测，再实现功能。
- Skill 只用于开发、评审、测试和验收流程；不会成为产品运行时依赖。
- MCP 只连接外部资料、协作和安全服务；业务写操作必须经过后端工具层、权限、状态机、幂等和审计。
- 公开数据、合成数据和用户数据始终保留 `source_type` 与来源元数据。
- RAG 外部资料必须经过下载、哈希、版本和权限检查后才可入库。
- 高风险动作始终停留在人工确认边界内。

## 统一交付物

- 每个 Step 的实现代码、测试、失败归因和运行记录。
- 每个 Agent 的职责、Prompt、工具白名单、输出 schema 和评测样例。
- 每个外部 MCP 的连接权限、数据边界、失败回退和审计记录。
- 每个阶段的版本号、数据版本、模型版本和配置版本。

## 分阶段计划

### Step 6：生成并登记合成业务数据

- 使用固定随机种子生成设施、位置、人员、供应商、SLA、报修、巡检、工单、验收、Agent 运行、审计和知识文档。
- 为每条记录写入 `source_type=synthetic`、`generator_version`、`generated_at` 和批次 ID。
- 用确定性校验验证外键、状态机、时间顺序、SLA 和幂等键。
- Skill：[`01 test-driven-development`](../Skills/01-test-driven-development.md)、[`02 qa-expert`](../Skills/02-qa-expert.md)、[`03 evaluation`](../Skills/03-evaluation.md)。
- MCP：不依赖外部 MCP；生成逻辑必须可离线复现。
- 完成条件：相同 seed 生成相同内容，重复运行不会污染 raw 数据。

### Step 7：建立数据清洗与统一映射

- 建立公开数据字段映射、日期和坐标清洗、行政区标准化、重复外部 ID 处理和字段统计。
- 生成 `facility_issue_events.csv`、缺失值报告、重复值报告和清洗批次清单。
- 原始文件只读，所有变换输出到 `data/processed`。
- Skill：[`03 evaluation`](../Skills/03-evaluation.md)、[`02 qa-expert`](../Skills/02-qa-expert.md)。
- MCP：[`03 Search Service`](../MCP/03-search-service.md) 只用于核对官方字段和规范，不能替代本地清洗脚本。
- 完成条件：来源、映射、过滤、哈希和失败行均可追溯。

### Step 8：设计 MySQL 数据模型

- 完成 users、roles、permissions、role_permissions、locations、facilities、citizen_reports、inspection_tasks、work_orders、vendors、technicians、sla_rules、acceptance_records、agent_runs、tool_calls 和 audit_logs。
- 加入状态、来源、版本、软删除、幂等键、区域、设施 ID、截止时间和 Agent 运行索引。
- 明确高风险动作、审计不可变事件和外键删除策略。
- Skill：[`04 sql-optimization`](../Skills/04-sql-optimization.md)、[`05 security-auditor`](../Skills/05-security-auditor.md)。
- MCP：不直接让外部 MCP 修改数据库；数据库操作通过迁移和受控脚本完成。
- 完成条件：schema review、外键检查、索引检查和权限边界评审通过。

### Step 9：实现数据库初始化与种子导入

- 建立迁移、初始化、批次导入和回滚入口。
- 导入设施、人员、供应商、SLA、公开事件、合成报修、巡检、工单、验收和审计数据。
- 校验外键关系、状态值、时间顺序、来源标签和幂等唯一性。
- Skill：[`02 qa-expert`](../Skills/02-qa-expert.md)、[`04 sql-optimization`](../Skills/04-sql-optimization.md)。
- MCP：不使用外部 MCP 写入数据库。
- 完成条件：空库可重复初始化，导入失败可定位并可恢复。

### Step 10：搭建 FastAPI 应用基础层

- 完成应用入口、配置加载、数据库 session、依赖注入、CORS、请求 ID、trace ID、结构化日志、健康检查和统一异常。
- `/health` 只反映进程存活，`/ready` 分别报告 MySQL、Chroma 和模型服务状态。
- 错误响应统一包含 `code`、`message`、`trace_id` 和 `retryable`。
- Skill：[`06 api-designer`](../Skills/06-api-designer.md)、[`07 api-documenter`](../Skills/07-api-documenter.md)、[`08 systematic-debugging`](../Skills/08-systematic-debugging.md)。
- MCP：[`02 OpenAI Developers`](../MCP/02-openai-developers.md) 仅用于官方客户端文档核对。
- 完成条件：API 启动、配置错误、依赖不可用和异常响应都有自动化测试。

### Step 11：实现认证与权限控制

- 实现 Token 校验、角色、菜单和接口权限映射。
- 在路由层、服务层和工具层重复执行权限校验。
- 限制用户区域和工单范围，记录登录、拒绝和人工确认事件。
- Skill：[`05 security-auditor`](../Skills/05-security-auditor.md)、[`08 systematic-debugging`](../Skills/08-systematic-debugging.md)。
- MCP：[`01 GitHub`](../MCP/01-github.md) 只用于代码协作和安全问题跟踪，不承载用户权限事实。
- 完成条件：越权、过期 Token、区域隔离和高风险动作拦截测试通过。

### Step 12：实现设施与问题上报模块

- 实现设施分页、筛选、详情、历史事件、附近设施和来源区分。
- 实现报修创建、查询、状态更新、重复问题检测和外部 ID 去重。
- 保存原始描述、结构化字段、位置和来源元数据。
- Skill：[`06 api-designer`](../Skills/06-api-designer.md)、[`04 sql-optimization`](../Skills/04-sql-optimization.md)、[`01 test-driven-development`](../Skills/01-test-driven-development.md)。
- MCP：[`03 Search Service`](../MCP/03-search-service.md) 可用于公开历史案例核对，结果先落本地数据层。
- 完成条件：公开事件、合成数据和内部报修在 API 与界面中可区分。

### Step 13：实现工单与巡检业务模块

- 实现巡检任务和工单完整状态机、SLA 截止时间、超时升级、维修证据和验收材料关联。
- 所有写操作支持幂等键、状态校验、容量冲突校验和审计。
- Skill：[`01 test-driven-development`](../Skills/01-test-driven-development.md)、[`04 sql-optimization`](../Skills/04-sql-optimization.md)、[`05 security-auditor`](../Skills/05-security-auditor.md)。
- MCP：不允许外部 MCP 直接执行派工、验收和关闭。
- 完成条件：合法/非法状态跳转、重复请求和高风险确认都有测试。

### Step 14：实现 RAG 文档上传与解析

- 支持 PDF、DOCX、Markdown、TXT 和 HTML，校验类型、大小、重复文件和内容安全。
- 保存来源、版本、设施类型、区域、生效日期、失效日期、上传人和解析状态。
- Skill：[`09 comprehensive-research-agent`](../Skills/09-comprehensive-research-agent.md)、[`05 security-auditor`](../Skills/05-security-auditor.md)。
- MCP：[`03 Search Service`](../MCP/03-search-service.md)、[`04 SharePoint`](../MCP/04-sharepoint.md)、[`05 Google Drive`](../MCP/05-google-drive.md)、[`06 Notion`](../MCP/06-notion.md)、[`07 Dropbox`](../MCP/07-dropbox.md) 可作为受控来源。
- 完成条件：解析失败可审计，来源权限和原始文件关联不丢失。

### Step 15：实现文本清洗与 Chunk 预览

- 清理页眉页脚、重复空白和不可见字符。
- 按标题、条款、段落、表格行和语义边界切分，默认 800 tokens、重叠 120 tokens。
- 保存 chunk_id、页码、标题、原文位置和父文档关系。
- Skill：[`09 comprehensive-research-agent`](../Skills/09-comprehensive-research-agent.md)、[`10 advanced-evaluation`](../Skills/10-advanced-evaluation.md)。
- MCP：文档来源 MCP 只负责获取，切块必须由本地可复现代码完成。
- 完成条件：可预览、可调整、可重新生成，并能定位回原文。

### Step 16：实现 Embedding 与 Chroma 入库

- 配置 OpenAI-compatible Embedding，加入批量、重试、超时、限流、缓存和模型版本记录。
- 失败时保留待重试状态，不写入不完整向量。
- Skill：[`10 advanced-evaluation`](../Skills/10-advanced-evaluation.md)、[`05 security-auditor`](../Skills/05-security-auditor.md)。
- MCP：[`02 OpenAI Developers`](../MCP/02-openai-developers.md) 用于官方 SDK 和模型参数核对；不让 MCP 直接写 Chroma。
- 完成条件：单文档重建、删除、失败重试和 metadata 完整性测试通过。

### Step 17：实现 RAG 检索与原文展示

- 实现查询改写、metadata 过滤、向量召回、关键词召回、去重、Rerank、Top-K 和原文回溯。
- 支持设施类型、区域、版本、生效日期和过期文档拦截。
- Skill：[`03 evaluation`](../Skills/03-evaluation.md)、[`10 advanced-evaluation`](../Skills/10-advanced-evaluation.md)、[`09 comprehensive-research-agent`](../Skills/09-comprehensive-research-agent.md)。
- MCP：外部文档连接器只提供来源，不参与最终排序和证据裁决。
- 完成条件：Recall@K、Hit Rate、MRR、来源正确率和 Chunk 可定位率可计算。

### Step 18：设计 Agent 状态与工具契约

- 定义 LangGraph 工作状态、计划、观察、引用、错误、停止原因和人工确认结构。
- 为工具定义参数、返回、错误、权限、风险等级、幂等和可重试契约。
- Skill：[`11 tool-design`](../Skills/11-tool-design.md)、[`12 multi-agent-patterns`](../Skills/12-multi-agent-patterns.md)、[`13 harness-engineering`](../Skills/13-harness-engineering.md)。
- MCP：[`02 OpenAI Developers`](../MCP/02-openai-developers.md) 只用于模型工具调用规范核对。
- 完成条件：每个工具都有 schema、白名单、风险等级和失败语义。

### Step 19：实现 Agent 工具层

- 实现设施、历史、报修、SLA、巡检、人员、供应商、工单、安全、验收和审计工具。
- 工具执行前统一校验 schema、权限、业务状态、风险和幂等。
- Skill：[`11 tool-design`](../Skills/11-tool-design.md)、[`05 security-auditor`](../Skills/05-security-auditor.md)、[`01 test-driven-development`](../Skills/01-test-driven-development.md)。
- MCP：通用 MCP 不直接替代项目工具，所有写操作进入项目审计链。
- 完成条件：工具参数非法、权限不足、重复调用和高风险调用测试通过。

### Step 20：实现 Supervisor 与 Agent 循环控制

- 创建 Supervisor，按意图路由 7 类 Agent，设置模型调用、工具调用、超时和无进展停止条件。
- 记录每次模型、工具、迭代、token、耗时和停止原因。
- Skill：[`12 multi-agent-patterns`](../Skills/12-multi-agent-patterns.md)、[`13 harness-engineering`](../Skills/13-harness-engineering.md)、[`10 advanced-evaluation`](../Skills/10-advanced-evaluation.md)。
- MCP：模型文档 MCP 只提供接口参考，不参与循环控制。
- 完成条件：证据不足、高风险和连续无进展时正确停止。

### Step 21：实现问题分诊与设施识别 Agent

- 实现分诊 Prompt、结构化输出、设施类型查询、重复报修和设施候选匹配。
- 低置信度进入人工确认，不直接绑定设施。
- Skill：[`12 multi-agent-patterns`](../Skills/12-multi-agent-patterns.md)、[`10 advanced-evaluation`](../Skills/10-advanced-evaluation.md)、[`05 security-auditor`](../Skills/05-security-auditor.md)。
- MCP：[`03 Search Service`](../MCP/03-search-service.md) 只补充可追溯历史案例。
- 完成条件：分诊和设施识别 Gold Set 建立并可重复评测。

### Step 22：实现 SLA、巡检计划与工单调度 Agent

- 实现 SLA 规则解释、优先级、截止时间、巡检建议、派工候选和冲突拦截。
- 对 P1、公共安全、重复派工、容量超限和人员冲突进入人工确认。
- Skill：[`12 multi-agent-patterns`](../Skills/12-multi-agent-patterns.md)、[`03 evaluation`](../Skills/03-evaluation.md)、[`05 security-auditor`](../Skills/05-security-auditor.md)。
- MCP：不允许外部 MCP 直接派工或改变工单状态。
- 完成条件：SLA、路由、工具参数和状态转移指标可计算。

### Step 23：实现安全作业与维修验收 Agent

- 实现安全风险标签、隔离措施、PPE、围挡、交通防护、验收建议和返工建议。
- 带电、高空、封路、燃气等场景只生成清单，不能自动批准。
- Skill：[`05 security-auditor`](../Skills/05-security-auditor.md)、[`11 tool-design`](../Skills/11-tool-design.md)、[`03 evaluation`](../Skills/03-evaluation.md)。
- MCP：[`08 Codex Security`](../MCP/08-codex-security.md) 可用于安全评测，不参与现场动作批准。
- 完成条件：高风险拦截、人工确认、返工和验收规则测试通过。

### Step 24：实现记忆与会话上下文

- 保存运行工作记忆、有限会话历史、滚动摘要、引用、工具结果和确认结果。
- 实现过期、删除、用户/角色/区域隔离和敏感信息脱敏。
- 不把全部对话自动写入长期向量库。
- Skill：[`14 memory-systems`](../Skills/14-memory-systems.md)、[`12 multi-agent-patterns`](../Skills/12-multi-agent-patterns.md)、[`05 security-auditor`](../Skills/05-security-auditor.md)。
- MCP：外部文档和协作 MCP 不得读取未授权会话记忆。
- 完成条件：隔离、过期、删除、脱敏和上下文恢复测试通过。

### Step 25：实现前端应用壳与菜单

- 完成布局、登录、角色菜单、Agent 菜单、RAG 菜单、运行记录和审计记录入口。
- Skill：[`15 vue-best-practices`](../Skills/15-vue-best-practices.md)、[`16 vue-router-best-practices`](../Skills/16-vue-router-best-practices.md)、[`17 vue-pinia-best-practices`](../Skills/17-vue-pinia-best-practices.md)、[`19 frontend-design`](../Skills/19-frontend-design.md)。
- MCP：[`09 Figma`](../MCP/09-figma.md) 可提供设计稿和组件标注；没有设计稿时使用本地设计规范。
- 完成条件：角色菜单、路由守卫、加载/失败/待确认/完成状态完整。

### Step 26：实现前端 Agent 与工单交互

- 实现报修输入、附件、运行阶段、工具轨迹、证据、人工确认、拒绝、取消、重试和 trace_id 展示。
- Skill：[`15 vue-best-practices`](../Skills/15-vue-best-practices.md)、[`18 vue-testing-best-practices`](../Skills/18-vue-testing-best-practices.md)、[`20 webapp-testing`](../Skills/20-webapp-testing.md)。
- MCP：不通过外部 MCP 执行业务动作；前端只调用受控 API。
- 完成条件：端到端交互和高风险确认流程可在浏览器中复现。

### Step 27：实现前端 RAG 管理与检索展示

- 实现上传、列表、解析状态、Chunk 预览、入库状态、过滤、检索、原文定位和失败提示。
- Skill：[`15 vue-best-practices`](../Skills/15-vue-best-practices.md)、[`18 vue-testing-best-practices`](../Skills/18-vue-testing-best-practices.md)、[`20 webapp-testing`](../Skills/20-webapp-testing.md)、[`10 advanced-evaluation`](../Skills/10-advanced-evaluation.md)。
- MCP：SharePoint、Drive、Notion 和 Dropbox 只作为授权文档来源。
- 完成条件：结果显示 score、文档名、页码、Chunk ID、metadata 和原文片段。

### Step 28：完善日志、审计和运行监控

- 统一记录 request_id、trace_id、agent_run_id、tool_call_id、user_id、耗时、token、成本、重试和错误。
- 增加健康、错误率、延迟、MySQL、Chroma 和模型告警。
- Skill：[`21 performance-engineer`](../Skills/21-performance-engineer.md)、[`22 code-reviewer`](../Skills/22-code-reviewer.md)、[`05 security-auditor`](../Skills/05-security-auditor.md)。
- MCP：[`08 Codex Security`](../MCP/08-codex-security.md)、[`10 Slack`](../MCP/10-slack.md)、[`11 Teams`](../MCP/11-teams.md) 可用于安全扫描和告警通知。
- 完成条件：敏感信息脱敏，审计不可变，告警可追踪且可关闭。

### Step 29：建立评测数据集与基准

- 建立分诊、设施匹配、SLA、调度、状态流转、RAG 和高风险样例 Gold Set。
- 固定数据、Prompt、模型和评测参数版本。
- Skill：[`03 evaluation`](../Skills/03-evaluation.md)、[`10 advanced-evaluation`](../Skills/10-advanced-evaluation.md)、[`02 qa-expert`](../Skills/02-qa-expert.md)。
- MCP：GitHub 可用于评测问题和失败样例跟踪；结果仍保存到 `evaluation/`。
- 完成条件：每项指标有数据集、脚本、阈值和失败归因。

### Step 30：执行 RAG 评测

- 计算 Recall@K、Hit Rate、MRR、来源正确率、Chunk 可定位率和过期文档拦截率。
- 对文档缺失、切分错误、metadata 过滤、排序错误和知识库缺失进行归因。
- Skill：[`10 advanced-evaluation`](../Skills/10-advanced-evaluation.md)、[`03 evaluation`](../Skills/03-evaluation.md)、[`22 code-reviewer`](../Skills/22-code-reviewer.md)。
- MCP：外部文档 MCP 不参与指标计算，避免评测结果不可复现。
- 完成条件：报告包含版本、指标、样例、错误归因和改进建议。

### Step 31：执行 Agent 评测与安全验证

- 评估分诊、设施、SLA、路由、工具参数、状态转移和高风险拦截。
- 测试提示注入、恶意文档、越权查询、敏感数据泄露、超时和服务不可用。
- Skill：[`05 security-auditor`](../Skills/05-security-auditor.md)、[`10 advanced-evaluation`](../Skills/10-advanced-evaluation.md)、[`02 qa-expert`](../Skills/02-qa-expert.md)。
- MCP：[`08 Codex Security`](../MCP/08-codex-security.md) 可辅助扫描，所有结论需回写评测报告。
- 完成条件：安全问题有严重级别、复现步骤、修复状态和回归测试。

### Step 32：执行端到端业务验收

- 从报修开始验证分诊、设施、SLA、巡检、派工、维修、验收、关闭和审计。
- 验证证据引用、高风险人工确认、重复请求、权限和来源标签。
- Skill：[`20 webapp-testing`](../Skills/20-webapp-testing.md)、[`23 verification-before-completion`](../Skills/23-verification-before-completion.md)、[`22 code-reviewer`](../Skills/22-code-reviewer.md)。
- MCP：GitHub 用于验收问题和证据归档，Slack/Teams 仅用于通知。
- 完成条件：MVP 清单逐项有可复核证据。

### Step 33：完成本地环境最终业务验收

- 在本地服务环境验证前端、后端、MySQL、Chroma、模型调用、权限、幂等、人工确认和审计。
- 修复验收发现的问题并重新执行回归测试。
- Skill：[`20 webapp-testing`](../Skills/20-webapp-testing.md)、[`23 verification-before-completion`](../Skills/23-verification-before-completion.md)、[`08 systematic-debugging`](../Skills/08-systematic-debugging.md)。
- MCP：不依赖外部 MCP，确保本地验收可离线重复。
- 完成条件：所有本地核心服务和端到端业务场景通过。

### Step 34：完成数据备份与恢复验证

- 备份 data、MySQL、Chroma、配置模板和评测结果，计算 SHA256。
- 在独立目录恢复并验证公开、合成、处理数据和 RAG 文档可读取。
- Skill：[`02 qa-expert`](../Skills/02-qa-expert.md)、[`23 verification-before-completion`](../Skills/23-verification-before-completion.md)。
- MCP：不使用外部 MCP 保存备份；外部存储若启用必须加密和记录权限。
- 完成条件：独立恢复环境可继续运行并通过关键检查。

### Step 35：整理项目文档与交付材料

- 更新 README、架构、数据来源、API、Agent、RAG、评测、失败归因、环境变量、备份和恢复说明。
- 清理密钥、缓存、临时文件和无关大文件。
- Skill：[`24 documentation-engineer`](../Skills/24-documentation-engineer.md)、[`22 code-reviewer`](../Skills/22-code-reviewer.md)。
- MCP：GitHub 用于发布说明和变更记录；Drive/SharePoint 可作为受控交付材料存储。
- 完成条件：新成员可按文档启动、验证、备份和恢复项目。

### Step 36：最后执行 Docker Compose 部署与发布验收

- 最后才编写完整 Compose，配置 backend、frontend、MySQL、Chroma、健康检查、持久化、网络和服务依赖。
- 构建镜像、启动服务、迁移和导入种子、导入 RAG 文档、执行向量化和完整验收。
- 验证重启持久化、异常健康检查、日志、Agent、RAG、工单、审计、备份和恢复。
- Skill：[`25 deployment-engineer`](../Skills/25-deployment-engineer.md)、[`23 verification-before-completion`](../Skills/23-verification-before-completion.md)、[`22 code-reviewer`](../Skills/22-code-reviewer.md)。
- MCP：GitHub 用于发布标签和 Release；Codex Security 用于发布前安全检查；Slack/Teams 可选用于发布通知。
- 完成条件：MVP 清单、服务重启、数据持久化和发布包全部通过。
