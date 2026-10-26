# 文件职责：调用 OpenAI 兼容 Embedding 接口。
# 后续实现批量向量化、重试、限流、模型版本记录和缓存。
# API Key 只能从环境变量读取，不能写入日志、metadata 或数据文件。
