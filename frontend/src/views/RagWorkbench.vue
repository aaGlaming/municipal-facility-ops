<template>
  <section>
    <h2>RAG 工作台</h2>
    <el-descriptions border :column="1">
      <el-descriptions-item label="链路">上传 → 解析 → 切块 → 向量化 → 检索</el-descriptions-item>
      <el-descriptions-item label="默认 Top-K">5</el-descriptions-item>
      <el-descriptions-item label="证据要求">结果需保留文档、页码、Chunk ID 和来源类型</el-descriptions-item>
    </el-descriptions>
  </section>
</template>
