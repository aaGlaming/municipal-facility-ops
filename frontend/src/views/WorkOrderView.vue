<script setup lang="ts">
import { onMounted, shallowRef } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '../api/client'

interface WorkOrder { id: string; priority: string; status: string; due_at?: string; assignee_id?: string; vendor_id?: string; facility_id?: string; problem_type?: string }
const rows = shallowRef<WorkOrder[]>([])
const loading = shallowRef(false)
const error = shallowRef<string | null>(null)
const nextStatus: Record<string, string> = { NEW: 'TRIAGED', TRIAGED: 'ASSIGNED', ASSIGNED: 'IN_PROGRESS', IN_PROGRESS: 'WAITING_CONFIRMATION', WAITING_CONFIRMATION: 'COMPLETED', COMPLETED: 'ACCEPTED' }
async function load(): Promise<void> { loading.value = true; error.value = null; try { rows.value = (await api.get<{ items: WorkOrder[] }>('/api/work-orders', { params: { page: 1, page_size: 50 } })).data.items } catch (cause: any) { error.value = cause?.response?.data?.message || '工单加载失败' } finally { loading.value = false } }
async function advance(order: WorkOrder): Promise<void> { const target = nextStatus[order.status]; if (!target) return; const confirmation = target === 'ACCEPTED' || target === 'COMPLETED'; if (confirmation) await ElMessageBox.confirm(`将工单推进到 ${target}，该动作需要授权确认。`, '确认状态变更', { type: 'warning' }); try { await api.post(`/api/work-orders/${order.id}/status`, { status: target, idempotency_key: `${order.id}:frontend:${target}:${Date.now()}`, human_confirmation: confirmation }); ElMessage.success(`工单已更新为 ${target}`); await load() } catch (cause: any) { ElMessage.error(cause?.response?.data?.message || '状态变更失败') } }
onMounted(load)
</script>

<template>
  <section class="work-order-page"><div class="page-heading"><div><p class="eyebrow">维修闭环</p><h1>工单中心</h1><p class="page-description">追踪 SLA 截止时间、派工人员和验收状态；每次状态变更都经过受控 API。</p></div><el-button :loading="loading" @click="load"><el-icon><Refresh /></el-icon>刷新</el-button></div><el-alert v-if="error" :title="error" type="error" show-icon :closable="false" /><el-card shadow="never"><el-table v-loading="loading" :data="rows" row-key="id" empty-text="当前区域暂无工单"><el-table-column prop="id" label="工单" width="190" /><el-table-column prop="problem_type" label="问题类型" min-width="130" /><el-table-column prop="priority" label="优先级" width="90"><template #default="scope"><el-tag :type="scope.row.priority === 'P1' ? 'danger' : scope.row.priority === 'P2' ? 'warning' : 'info'">{{ scope.row.priority }}</el-tag></template></el-table-column><el-table-column prop="status" label="状态" width="150" /><el-table-column prop="due_at" label="SLA 截止" min-width="170" /><el-table-column prop="assignee_id" label="派工人员" width="130"><template #default="scope">{{ scope.row.assignee_id || '待派工' }}</template></el-table-column><el-table-column label="操作" width="130" fixed="right"><template #default="scope"><el-button v-if="nextStatus[scope.row.status]" link type="primary" @click="advance(scope.row)">{{ nextStatus[scope.row.status] }}</el-button><span v-else class="muted-cell">已终态</span></template></el-table-column></el-table></el-card></section>
</template>

<style scoped>.work-order-page :deep(.el-card) { margin-top: 18px; }.muted-cell { color: #9aaab2; font-size: 12px; }</style>
