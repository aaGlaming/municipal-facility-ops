# Step24：记忆与会话上下文

## 实现内容

- `SessionMemoryStore` 提供会话记忆的创建、读取、追加、删除和过期清理。
- 记忆按 `session_id`、用户、角色和区域隔离；未经授权的用户、角色或区域无法读取会话内容。
- 记忆保存有限消息、滚动摘要、RAG 引用、工具结果和人工确认结果；消息超过窗口后压缩到摘要，不无限增长。
- 支持 `expires_at` TTL、软删除清空和物理过期清理。
- 对密码、Token、Secret、API Key、Authorization、Cookie、Bearer/JWT 和邮箱进行脱敏。
- 记忆只保存在关系型会话表，不会自动写入 Chroma 或其他长期向量库。

## 数据结构

- `SessionMemory`：`session_memories` 表，保存会话所有者、角色、区域、摘要、有限上下文、版本、过期和删除时间。
- `MemoryMessage`、`MemoryAppend`、`MemoryContext`：严格的输入和恢复契约。
- 数据库增量迁移：`infra/mysql/init/008_step24_session_memories.sql`。

## 使用示例

```python
store = SessionMemoryStore(ttl_seconds=86400, max_messages=20)
store.open(db, principal, request, "SESSION-1", region="中心区")
context = store.append(db, principal, request, "SESSION-1", payload)
restored = store.load(db, principal, request, "SESSION-1")
```

## 验证

- Step24 定向测试：3 passed
- 全量测试：75 passed
- 覆盖用户/角色/区域隔离、过期、删除、脱敏、滚动摘要和上下文恢复。
