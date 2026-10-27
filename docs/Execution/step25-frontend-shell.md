# Step25：前端应用壳与菜单

## 实现内容

- 使用 Vue 3 Composition API、TypeScript、Vue Router 和 Element Plus 完成响应式应用壳。
- 深色导航栏按“值守中心 / Agent 编排 / 知识与检索 / 可追溯记录”分组展示菜单，菜单根据当前用户权限动态过滤。
- 新增登录页，调用 `/api/auth/login` 和 `/api/auth/me`；Token 仅保存在运行时内存，不写入 localStorage。
- 路由守卫校验登录状态和权限，未登录跳转登录页，无权限路由回到值守总览。
- 增加问题分诊、设施识别、SLA 判断、巡检计划、工单调度、安全作业、维修验收、RAG 文档/Chunk/向量/检索、运行记录和审计记录入口。
- 统一模块页展示加载中、待人工确认、失败和完成状态边界，为后续业务交互保留明确入口。
- Axios 客户端自动附加 `X-Request-Id` 和内存中的 Bearer Token。

## 验证

- `npm run type-check`：通过
- `npm run build`：通过
- 构建产物未提交，`dist/` 保持忽略。
