<template>
  <section>
    <h2>Agent 工作台</h2>
    <el-alert title="当前为可运行骨架，Agent 编排和人工确认流程将在后续阶段接入。" type="info" :closable="false" />
    <el-card class="card"><el-statistic title="运行控制" value="8 / 16 / 90s" /></el-card>
  </section>
</template>

<style scoped>.card { margin-top: 20px; max-width: 420px; }</style>
