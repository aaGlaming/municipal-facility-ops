<template>
  <section>
    <h2>设施与问题</h2>
    <el-table :data="rows" stripe><el-table-column prop="id" label="编号" /><el-table-column prop="type" label="类型" /><el-table-column prop="source_type" label="来源" /></el-table>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { api } from '../api/client'

const rows = ref<Record<string, string>[]>([])
api.get('/api/facilities').then(({ data }) => { rows.value = data.items }).catch(() => { rows.value = [] })
</script>
