> **Skill/MCP 同步说明：** Step 6～Step 36 的执行计划已为每个步骤标注适用 Skill 和 MCP。Skill 文档位于 `docs/Skills/`，MCP 文档位于 `docs/MCP/`；MCP 只用于受控资料、协作、安全和通知，不能绕过项目权限、状态机、幂等和审计。

# step1：确认项目范围与验收边界

- 确认项目名称为市政设施巡检与维修平台。
- 确认覆盖路灯、交通信号、道路破损、井盖、人行道、排水、垃圾设施和绿化设施。
- 确认用户角色包括调度员、巡检员、维修人员、供应商、管理员和审计人员。
- 确认 MVP 验收范围包括至少 5 个 Agent、完整 RAG 链路、工单状态流转、人工确认和审计；Docker Compose 部署安排在全部功能完成后。
- 确认公开数据、合成数据、用户上传数据在系统中分开标识。

# step2：创建项目仓库与基础目录

- 创建 `municipal-facility-ops` 项目目录。
- 创建 backend、frontend、data、docs、scripts、infra、evaluation、logs 和 uploads 目录。
- 初始化 Git 仓库并创建开发分支。
- 创建 README、环境变量示例、忽略文件和项目版本文件。
- 建立后端、前端和数据脚本的占位结构，部署目录只保留待最后阶段使用的占位文件。

# step3：配置本地开发环境

- 使用指定 Python 虚拟环境安装后端依赖。
- 安装 FastAPI、SQLAlchemy、MySQL 驱动、Chroma、LangChain、LangGraph 和 OpenAI 兼容客户端依赖。
- 安装 Node.js、Vue、Element Plus、TypeScript、Axios 和 Vue Router 依赖。
- 配置代码格式化、静态检查、类型检查和测试命令。
- 配置 `.env`，填入数据库、Chroma、LLM、Embedding 和运行控制参数。
- 确认真实 API Key 不进入 Git、日志和数据文件。

# step4：准备本地基础依赖服务

- 使用本地安装或已有服务准备 MySQL。
- 使用本地进程或已有服务准备 Chroma。
- 配置本地数据库、向量库和模型 API 的连接参数。
- 验证数据库连接、Chroma 连接和模型 API 连通性。
- 暂不编写、构建或启动 Docker Compose。

# step5：下载并登记公开数据

- 下载 NYC 311 服务请求数据。
- 下载 NYC 路灯和交通信号相关报修数据。
- 下载 NYC DOT 坑洞维修工单数据。
- 下载 NYC DOT 设施数据说明和 Open311 规范文档。
- 将原始数据保存到 `data/raw/public` 和 `data/raw/docs`。
- 记录来源 URL、原始数据集 ID、筛选条件、下载时间、文件大小、行数和 SHA256。
- 保留公开数据原样，不在原始目录中修改字段或内容。

# step6：生成并登记合成业务数据

- 编写固定随机种子的合成数据生成流程。
- 生成设施资产和地理位置数据。
- 生成维修班组、维修人员和供应商数据。
- 生成 SLA 规则和优先级规则。
- 生成市民报修、巡检任务、维修工单、验收记录和审计记录。
- 生成 Agent 运行记录和 RAG 演示知识文档。
- 为每条合成记录写入 `source_type=synthetic`、生成器版本和生成时间。

- **建议 Skill：** [01-test-driven-development](Skills/01-test-driven-development.md)、[02-qa-expert](Skills/02-qa-expert.md)、[03-evaluation](Skills/03-evaluation.md)

# step7：建立数据清洗与统一映射

- 读取公开数据并统一事件编号、问题类别、状态、时间、机构、地址、行政区和坐标字段。
- 处理不同来源的日期格式、行政区缩写、空坐标和重复外部 ID。
- 生成 `facility_issue_events.csv` 统一事件表。
- 生成字段统计、缺失值统计、重复值统计和清洗批次信息。
- 将清洗结果保存到 `data/processed`。
- 禁止覆盖 `data/raw` 原始文件。

- **建议 Skill：** [03-evaluation](Skills/03-evaluation.md)、[02-qa-expert](Skills/02-qa-expert.md)
- **建议 MCP：** [03-search-service](MCP/03-search-service.md)

# step8：设计 MySQL 数据模型

- 创建 users、roles、permissions 和 role_permissions 表。
- 创建 facilities 和 locations 表。
- 创建 citizen_reports 表。
- 创建 inspection_tasks 表。
- 创建 work_orders 表。
- 创建 vendors、technicians 和 sla_rules 表。
- 创建 acceptance_records 表。
- 创建 agent_runs、tool_calls 和 audit_logs 表。
- 为状态、设施 ID、区域、外部 ID、幂等键、创建时间和截止时间建立索引。
- 为来源类型、来源系统、数据版本和软删除字段留出字段。

- **建议 Skill：** [04-sql-optimization](Skills/04-sql-optimization.md)、[05-security-auditor](Skills/05-security-auditor.md)

# step9：实现数据库初始化与种子导入

- 编写数据库迁移和初始化脚本。
- 导入设施、人员、供应商和 SLA 合成数据。
- 导入公开事件和合成报修数据。
- 导入巡检任务、工单、验收和审计种子数据。
- 校验外键关系、状态值、时间顺序和幂等键唯一性。
- 为每次导入生成批次 ID 和导入日志。

- **建议 Skill：** [02-qa-expert](Skills/02-qa-expert.md)、[04-sql-optimization](Skills/04-sql-optimization.md)

# step10：搭建 FastAPI 应用基础层

- 创建 FastAPI 应用入口。
- 注册统一异常处理、请求 ID、CORS、日志和健康检查中间件。
- 创建配置加载、数据库 session、模型基类和依赖注入模块。
- 创建统一响应格式和错误码。
- 为错误响应增加 `code`、`message`、`trace_id` 和 `retryable`。
- 实现 `/health` 和 `/ready` 接口。

- **建议 Skill：** [06-api-designer](Skills/06-api-designer.md)、[07-api-documenter](Skills/07-api-documenter.md)、[08-systematic-debugging](Skills/08-systematic-debugging.md)
- **建议 MCP：** [02-openai-developers](MCP/02-openai-developers.md)

# step11：实现认证与权限控制

- 实现用户认证和 Token 校验。
- 实现角色、菜单和接口权限映射。
- 限制调度员、巡检员、维修人员、供应商、管理员和审计人员的数据范围。
- 在路由层、服务层和工具层分别执行权限校验。
- 为高风险动作配置人工确认权限。
- 记录登录、权限拒绝和人工确认事件。

- **建议 Skill：** [05-security-auditor](Skills/05-security-auditor.md)、[08-systematic-debugging](Skills/08-systematic-debugging.md)
- **建议 MCP：** [01-github](MCP/01-github.md)

# step12：实现设施与问题上报模块

- 实现设施分页、筛选、详情和历史事件查询。
- 实现按地址、坐标、类型和区域查询附近设施。
- 实现市民问题上报创建、查询和状态更新。
- 实现公开事件导入和内部报修的来源区分。
- 实现重复问题检测和外部 ID 去重。
- 为问题上报保存原始描述、结构化字段和来源信息。

- **建议 Skill：** [06-api-designer](Skills/06-api-designer.md)、[04-sql-optimization](Skills/04-sql-optimization.md)、[01-test-driven-development](Skills/01-test-driven-development.md)
- **建议 MCP：** [03-search-service](MCP/03-search-service.md)

# step13：实现工单与巡检业务模块

- 实现巡检任务创建、分配、执行、延期和完成。
- 实现工单创建、分诊、派工、进行中、待确认、完成、验收、关闭和返工状态。
- 实现拒绝、阻塞、升级和取消异常状态。
- 实现状态机校验，禁止非法状态跳转。
- 实现 SLA 截止时间计算和超时升级。
- 实现维修证据、处理说明和验收材料关联。

- **建议 Skill：** [01-test-driven-development](Skills/01-test-driven-development.md)、[04-sql-optimization](Skills/04-sql-optimization.md)、[05-security-auditor](Skills/05-security-auditor.md)

# step14：实现 RAG 文档上传与解析

- 支持 PDF、DOCX、Markdown、TXT 和 HTML 文件上传。
- 校验文件类型、文件大小、文件名、内容安全和重复文件。
- 保存文档来源、上传人、设施类型、区域、生效日期、失效日期和版本。
- 解析文本、页码、标题、段落和表格。
- 对解析失败文档记录错误状态和失败原因。
- 将原始文件和解析结果建立关联。

- **建议 Skill：** [09-comprehensive-research-agent](Skills/09-comprehensive-research-agent.md)、[05-security-auditor](Skills/05-security-auditor.md)
- **建议 MCP：** [03-search-service](MCP/03-search-service.md)、[04-sharepoint](MCP/04-sharepoint.md)、[05-google-drive](MCP/05-google-drive.md)、[06-notion](MCP/06-notion.md)、[07-dropbox](MCP/07-dropbox.md)

# step15：实现文本清洗与 Chunk 预览

- 清理重复空白、页眉页脚、不可见字符和无意义内容。
- 按标题、段落、条款、表格行和语义边界切分文本。
- 使用目标 800 tokens、重叠 120 tokens 作为初始参数。
- 保存 chunk_id、document_id、chunk_index、页码、标题和原文位置。
- 提供独立的 Chunk 预览菜单。
- 允许在入库前查看、调整和重新生成 Chunk。

- **建议 Skill：** [09-comprehensive-research-agent](Skills/09-comprehensive-research-agent.md)、[10-advanced-evaluation](Skills/10-advanced-evaluation.md)
- **建议 MCP：** [03-search-service](MCP/03-search-service.md)、[04-sharepoint](MCP/04-sharepoint.md)、[05-google-drive](MCP/05-google-drive.md)、[06-notion](MCP/06-notion.md)、[07-dropbox](MCP/07-dropbox.md)

# step16：实现 Embedding 与 Chroma 入库

- 配置 OpenAI 兼容 Embedding 模型。
- 实现批量向量化、重试、超时、限流和缓存。
- 将 Chunk、向量和 metadata 写入 Chroma。
- 记录 Embedding 模型版本、文档版本和入库批次。
- 支持单文档重建索引和文档删除。
- Embedding 失败时保留待重试状态，不写入不完整结果。

- **建议 Skill：** [10-advanced-evaluation](Skills/10-advanced-evaluation.md)、[05-security-auditor](Skills/05-security-auditor.md)
- **建议 MCP：** [02-openai-developers](MCP/02-openai-developers.md)

# step17：实现 RAG 检索与原文展示

- 实现查询改写和查询字段提取。
- 实现设施类型、区域、版本和生效日期过滤。
- 实现向量召回、关键词召回、去重和候选合并。
- 实现可选 Rerank 和 Top-K 取值控制。
- 默认返回 Top-K 为 5。
- 返回文档名、页码、Chunk ID、相似度、metadata 和原文片段。
- 实现无召回、过期文档、文档解析失败和检索服务不可用提示。
- 提供独立的检索调试菜单。

- **建议 Skill：** [03-evaluation](Skills/03-evaluation.md)、[10-advanced-evaluation](Skills/10-advanced-evaluation.md)、[09-comprehensive-research-agent](Skills/09-comprehensive-research-agent.md)
- **建议 MCP：** [03-search-service](MCP/03-search-service.md)、[04-sharepoint](MCP/04-sharepoint.md)、[05-google-drive](MCP/05-google-drive.md)、[06-notion](MCP/06-notion.md)、[07-dropbox](MCP/07-dropbox.md)

# step18：设计 Agent 状态与工具契约

- 定义 LangGraph 工作状态字段。
- 定义 Agent 请求、计划、观察结果、引用证据、错误和停止原因。
- 为每个工具定义名称、参数 schema、返回 schema 和错误 schema。
- 为工具定义只读、写入、高风险和人工确认等级。
- 为写工具定义幂等键格式和重复执行结果。
- 为每个工具定义可重试错误和不可重试错误。

- **建议 Skill：** [11-tool-design](Skills/11-tool-design.md)、[12-multi-agent-patterns](Skills/12-multi-agent-patterns.md)、[13-harness-engineering](Skills/13-harness-engineering.md)
- **建议 MCP：** [02-openai-developers](MCP/02-openai-developers.md)

# step19：实现 Agent 工具层

- 实现设施查询工具。
- 实现历史事件查询工具。
- 实现问题上报创建工具。
- 实现 SLA 查询、截止时间计算和升级工具。
- 实现巡检任务创建和任务结果记录工具。
- 实现维修人员和供应商能力查询工具。
- 实现工单创建、派工、状态更新和验收工具。
- 实现安全规范查询、许可检查和安全清单工具。
- 实现审计事件和人工确认工具。
- 在工具执行前统一执行 schema、业务规则、权限、风险和幂等校验。

- **建议 Skill：** [11-tool-design](Skills/11-tool-design.md)、[05-security-auditor](Skills/05-security-auditor.md)、[01-test-driven-development](Skills/01-test-driven-development.md)

# step20：实现 Supervisor 与 Agent 循环控制

- 创建 LangGraph Supervisor。
- 根据用户意图选择对应业务 Agent。
- 为每个节点配置输入、输出、工具白名单和失败转移。
- 设置单次任务最多 8 次模型调用。
- 设置单次任务最多 16 次工具调用。
- 设置默认 90 秒超时。
- 在连续两次没有业务进展时停止。
- 在证据不足、高风险或需要人工确认时停止并返回待确认状态。
- 记录每次模型调用、工具调用、迭代次数、token、耗时和停止原因。

- **建议 Skill：** [12-multi-agent-patterns](Skills/12-multi-agent-patterns.md)、[13-harness-engineering](Skills/13-harness-engineering.md)、[10-advanced-evaluation](Skills/10-advanced-evaluation.md)
- **建议 MCP：** [02-openai-developers](MCP/02-openai-developers.md)

# step21：实现问题分诊与设施识别 Agent

- 编写问题分诊 Agent Prompt。
- 将自然语言问题转换为标准问题类别、摘要、位置和缺失字段。
- 调用设施类型查询和问题创建工具。
- 调用设施查询、历史事件和附近设施工具。
- 输出候选设施、匹配置信度和匹配依据。
- 低置信度时转人工确认，不直接绑定设施。
- 为分诊和设施识别建立评测样例。

- **建议 Skill：** [12-multi-agent-patterns](Skills/12-multi-agent-patterns.md)、[10-advanced-evaluation](Skills/10-advanced-evaluation.md)、[05-security-auditor](Skills/05-security-auditor.md)
- **建议 MCP：** [03-search-service](MCP/03-search-service.md)

# step22：实现 SLA、巡检计划与工单调度 Agent

- 编写 SLA Agent Prompt 和结构化输出 schema。
- 根据安全影响、影响范围和问题类型生成优先级和截止时间。
- 对 P1 和公共安全问题触发人工确认。
- 编写巡检计划 Agent Prompt。
- 根据区域、问题类型、风险和人员容量生成巡检任务建议。
- 编写工单调度 Agent Prompt。
- 根据技能、区域、工作量、供应商能力和 SLA 生成派工建议。
- 对重复派工、人员冲突和容量超限进行拦截。

- **建议 Skill：** [12-multi-agent-patterns](Skills/12-multi-agent-patterns.md)、[03-evaluation](Skills/03-evaluation.md)、[05-security-auditor](Skills/05-security-auditor.md)

# step23：实现安全作业与维修验收 Agent

- 编写安全作业 Agent Prompt。
- 根据设施类型和现场信息生成风险标签、隔离措施、PPE、围挡和交通防护要求。
- 对带电、高空、道路封闭和燃气相关场景只生成检查清单。
- 编写维修验收 Agent Prompt。
- 检查维修说明、完成时间、照片、材料和验收规则。
- 输出通过、返工或有条件通过建议。
- 最终关闭动作要求验收人员确认。

- **建议 Skill：** [05-security-auditor](Skills/05-security-auditor.md)、[11-tool-design](Skills/11-tool-design.md)、[03-evaluation](Skills/03-evaluation.md)
- **建议 MCP：** [08-codex-security](MCP/08-codex-security.md)

# step24：实现记忆与会话上下文

- 保存当前 Agent 运行的工作记忆。
- 保存有限轮次的会话历史和滚动摘要。
- 保存检索引用、工具结果和人工确认结果。
- 设置会话过期和删除入口。
- 按用户、角色和业务区域隔离会话数据。
- 对地址、联系方式和报修人信息执行脱敏。
- 不把全部对话自动写入长期向量库。

- **建议 Skill：** [14-memory-systems](Skills/14-memory-systems.md)、[12-multi-agent-patterns](Skills/12-multi-agent-patterns.md)、[05-security-auditor](Skills/05-security-auditor.md)

# step25：实现前端应用壳与菜单

- 创建 Vue 应用入口和全局布局。
- 配置 Element Plus、路由、状态管理和 API 客户端。
- 创建首页看板。
- 创建问题分诊、设施识别、SLA 判断、巡检计划、工单调度、安全作业审批和维修验收菜单。
- 创建 RAG 文档上传、Chunk 切块预览、向量化入库、向量检索和原文片段查看菜单。
- 创建 Agent 运行记录和审计记录菜单。
- 配置登录、角色和菜单权限守卫。

- **建议 Skill：** [15-vue-best-practices](Skills/15-vue-best-practices.md)、[16-vue-router-best-practices](Skills/16-vue-router-best-practices.md)、[17-vue-pinia-best-practices](Skills/17-vue-pinia-best-practices.md)、[19-frontend-design](Skills/19-frontend-design.md)
- **建议 MCP：** [09-figma](MCP/09-figma.md)

# step26：实现前端 Agent 与工单交互

- 实现报修文本输入、位置输入和附件上传。
- 展示 Agent 运行阶段、当前节点、工具调用、引用证据和最终建议。
- 展示待人工确认动作。
- 实现人工确认、拒绝、取消和重试操作。
- 展示工单状态、SLA 截止时间、派工人员和验收结果。
- 为每次 Agent 操作显示 trace_id。
- 为加载、成功、失败、待确认和完成状态提供反馈。

- **建议 Skill：** [15-vue-best-practices](Skills/15-vue-best-practices.md)、[18-vue-testing-best-practices](Skills/18-vue-testing-best-practices.md)、[20-webapp-testing](Skills/20-webapp-testing.md)

# step27：实现前端 RAG 管理与检索展示

- 实现文档上传和文档列表。
- 展示解析状态、切块数量、入库状态和版本。
- 实现 Chunk 预览、筛选和原文定位。
- 实现检索词、设施类型、区域、版本和 Top-K 设置。
- 展示召回、去重、Rerank 和最终结果。
- 支持展开查看文档原文片段、页码、Chunk ID 和 metadata。
- 展示无结果、过期文档和检索失败提示。

- **建议 Skill：** [15-vue-best-practices](Skills/15-vue-best-practices.md)、[18-vue-testing-best-practices](Skills/18-vue-testing-best-practices.md)、[20-webapp-testing](Skills/20-webapp-testing.md)、[10-advanced-evaluation](Skills/10-advanced-evaluation.md)
- **建议 MCP：** [04-sharepoint](MCP/04-sharepoint.md)、[05-google-drive](MCP/05-google-drive.md)、[06-notion](MCP/06-notion.md)、[07-dropbox](MCP/07-dropbox.md)

# step28：完善日志、审计和运行监控

- 统一记录 request_id、trace_id、agent_run_id、tool_call_id 和 user_id。
- 记录模型、Embedding、检索、工具和数据库耗时。
- 记录输入输出 token、错误类型、重试次数和成本估算。
- 记录权限拒绝、人工确认、状态变更和审计结果。
- 对日志中的密钥、Token、联系方式和地址执行脱敏。
- 增加服务健康、错误率、延迟、Chroma 状态、MySQL 状态和模型调用告警。
- 区分可重试错误、不可重试错误和人工处理错误。

- **建议 Skill：** [21-performance-engineer](Skills/21-performance-engineer.md)、[22-code-reviewer](Skills/22-code-reviewer.md)、[05-security-auditor](Skills/05-security-auditor.md)
- **建议 MCP：** [08-codex-security](MCP/08-codex-security.md)、[10-slack](MCP/10-slack.md)、[11-teams](MCP/11-teams.md)

# step29：建立评测数据集与基准

- 建立问题分诊 Gold Set。
- 建立设施匹配 Gold Set。
- 建立 SLA 判断 Gold Set。
- 建立工单调度和状态流转样例。
- 建立 RAG 查询、正确文档、正确 Chunk 和有效时间范围标注。
- 建立高风险操作和权限拒绝样例。
- 固定数据版本、Prompt 版本、模型版本和评测参数。

- **建议 Skill：** [03-evaluation](Skills/03-evaluation.md)、[10-advanced-evaluation](Skills/10-advanced-evaluation.md)、[02-qa-expert](Skills/02-qa-expert.md)
- **建议 MCP：** [01-github](MCP/01-github.md)

# step30：执行 RAG 评测

- 计算 Recall@K、Hit Rate 和 MRR。
- 计算来源文档正确率和 Chunk 可定位率。
- 计算过期文档拦截率。
- 对无召回、召回跑偏、Chunk 边界错误和知识库缺失进行归因。
- 使用人工抽检检查原文引用、回答忠实度和答案相关性。
- 保存每次评测结果、失败样例和版本信息。

- **建议 Skill：** [10-advanced-evaluation](Skills/10-advanced-evaluation.md)、[03-evaluation](Skills/03-evaluation.md)、[22-code-reviewer](Skills/22-code-reviewer.md)

# step31：执行 Agent 评测与安全验证

- 评估分诊准确率、设施匹配准确率和 SLA 判断准确率。
- 评估工单路由准确率、工具参数合法率和状态转移正确率。
- 测试 Schema 非法、权限不足、重复调用和幂等冲突。
- 测试高风险作业、人工确认、拒绝和取消流程。
- 测试提示注入、恶意文档、越权查询和敏感数据泄露。
- 测试模型超时、工具失败、Chroma 不可用、MySQL 断开和外部 API 不可用。
- 验证错误返回包含 code、message、trace_id 和 retryable。

- **建议 Skill：** [05-security-auditor](Skills/05-security-auditor.md)、[10-advanced-evaluation](Skills/10-advanced-evaluation.md)、[02-qa-expert](Skills/02-qa-expert.md)
- **建议 MCP：** [08-codex-security](MCP/08-codex-security.md)

# step32：执行端到端业务验收

- 从问题上报开始执行完整流程。
- 完成问题分诊、设施识别、SLA 判断、巡检、派工、维修、验收、关闭和审计。
- 验证每个 Agent 可以调用 RAG 并展示证据片段。
- 验证高风险动作在人工确认前不会执行。
- 验证重复请求不会生成重复工单或重复派工。
- 验证普通人员、调度员、维修人员、管理员和审计人员的数据权限。
- 验证公开、合成和用户数据的来源标签在前端可见。

- **建议 Skill：** [20-webapp-testing](Skills/20-webapp-testing.md)、[23-verification-before-completion](Skills/23-verification-before-completion.md)、[22-code-reviewer](Skills/22-code-reviewer.md)
- **建议 MCP：** [01-github](MCP/01-github.md)、[10-slack](MCP/10-slack.md)、[11-teams](MCP/11-teams.md)

# step33：完成本地环境最终业务验收

- 在本地服务环境中执行完整问题上报、分诊、设施识别、SLA 判断、巡检、派工、维修、验收和关闭流程。
- 验证前端菜单、后端接口、MySQL 查询、Chroma 检索和模型调用全部可用。
- 验证每个 Agent 都能调用 RAG 并返回可定位的原文证据。
- 验证高风险动作、权限拒绝、人工确认、幂等和审计流程。
- 修复本地验收中发现的功能、数据、日志和权限问题。

- **建议 Skill：** [20-webapp-testing](Skills/20-webapp-testing.md)、[23-verification-before-completion](Skills/23-verification-before-completion.md)、[08-systematic-debugging](Skills/08-systematic-debugging.md)

# step34：完成数据备份与恢复验证

- 备份项目 `data/` 目录。
- 备份 MySQL 数据库。
- 备份 Chroma 持久化目录。
- 备份环境变量模板、数据清单和评测结果。
- 对备份文件计算 SHA256。
- 在独立目录恢复数据并验证公开数据、合成数据、统一处理数据和 RAG 文档可读取。
- 在本地服务环境中恢复数据并验证系统可以继续运行。

- **建议 Skill：** [02-qa-expert](Skills/02-qa-expert.md)、[23-verification-before-completion](Skills/23-verification-before-completion.md)

# step35：整理项目文档与交付材料

- 更新项目 README。
- 更新架构、数据来源、数据字典、API、Agent 和 RAG 说明。
- 记录每个 Agent 的职责、Prompt、工具白名单和输出 schema。
- 记录数据来源、合成规则、版本和哈希清单。
- 记录评测数据集、指标、失败归因和已知问题。
- 记录本地环境变量、启动命令、备份命令和恢复命令。
- 清理临时文件、密钥、缓存、编译产物和大体积无关文件。

- **建议 Skill：** [24-documentation-engineer](Skills/24-documentation-engineer.md)、[22-code-reviewer](Skills/22-code-reviewer.md)
- **建议 MCP：** [01-github](MCP/01-github.md)、[04-sharepoint](MCP/04-sharepoint.md)、[05-google-drive](MCP/05-google-drive.md)

# step36：最后执行 Docker Compose 部署与发布验收

- 编写并确认 backend、frontend、MySQL 和 Chroma 的 Docker Compose 配置。
- 配置镜像、网络、健康检查、持久化卷、环境变量和服务依赖。
- 构建 backend 和 frontend 镜像。
- 启动 frontend、backend、MySQL 和 Chroma。
- 执行数据库迁移和种子导入。
- 导入 RAG 文档并执行向量化入库。
- 验证前端菜单、后端接口、数据库查询、Agent 调用和检索结果。
- 验证服务重启后 MySQL 和 Chroma 数据仍然存在。
- 验证服务异常时健康检查、日志和错误提示正常。
- 核对 MVP 验收清单全部通过。
- 核对至少 5 个 Agent 具有独立菜单、Prompt、工具白名单和评测样例。
- 核对 RAG 上传、切块、向量化、检索、结果展示和原文查看全部可用。
- 核对 Agent 工具调用具备 schema、权限、风险、人工确认、幂等和审计控制。
- 核对工单从 NEW 到 CLOSED 的状态流转可追踪。
- 核对日志、审计、指标、备份和恢复流程可用。
- 创建发布标签并记录版本号、数据版本、模型版本和配置版本。
- 生成最终交付包和启动说明。

- **建议 Skill：** [25-deployment-engineer](Skills/25-deployment-engineer.md)、[23-verification-before-completion](Skills/23-verification-before-completion.md)、[22-code-reviewer](Skills/22-code-reviewer.md)
- **建议 MCP：** [01-github](MCP/01-github.md)、[08-codex-security](MCP/08-codex-security.md)、[10-slack](MCP/10-slack.md)、[11-teams](MCP/11-teams.md)
