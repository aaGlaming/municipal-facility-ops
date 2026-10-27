<script setup lang="ts">
import { computed, onMounted, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '../api/client'
import { useAppStore } from '../stores/app'

interface RunRow { id: string; agent_name: string; trace_id: string; user_id?: string; region?: string; status: string; iterations: number; input_tokens: number; output_tokens: number; stop_reason?: string; started_at: string; finished_at?: string; duration_ms?: number }
interface AuditRow { event_type: string; occurred_at: string; subject?: string; request_id?: string; trace_id?: string; details?: Record<string, unknown> }
interface Overview { requests: number; error_count: number; error_rate: number; latency_ms: { p50: number; p95: number }; dependencies: Record<string, string>; active_alert_count: number; alerts: Array<{ id: string; code: string; message: string; status: string; details: Record<string, unknown> }> }

const route = useRoute()
const router = useRouter()
const store = useAppStore()
const moduleName = computed(() => String(route.params.module || 'runs'))
const runs = shallowRef<RunRow[]>([])
const audits = shallowRef<AuditRow[]>([])
const overview = shallowRef<Overview | null>(null)
const loading = shallowRef(false)
const error = shallowRef<string | null>(null)
const visibleTabs = computed(() => [
  store.can('agent:read') ? { key: 'runs', label: '运行监控' } : null,
  store.can('audit:read') ? { key: 'audit', label: '审计记录' } : null,
].filter(Boolean) as Array<{ key: string; label: string }>)

async function load(): Promise<void> {
  loading.value = true; error.value = null
  try {
    if (store.can('agent:read')) {
      const [runResponse, overviewResponse] = await Promise.all([
        api.get<{ items: RunRow[] }>('/api/monitoring/runs', { params: { page: 1, page_size: 50 } }),
        api.get<{ metrics: Overview }>('/api/monitoring/overview'),
      ])
      runs.value = runResponse.data.items; overview.value = overviewResponse.data.metrics
    }
    if (moduleName.value === 'audit' && store.can('audit:read')) audits.value = (await api.get<{ items: AuditRow[] }>('/api/monitoring/audit')).data.items
  } catch (cause: any) { error.value = cause?.response?.data?.message || '监控记录加载失败' } finally { loading.value = false }
}
async function closeAlert(id: string): Promise<void> {
  try { await api.post(`/api/monitoring/alerts/${id}/close`); ElMessage.success('告警已关闭'); await load() } catch (cause: any) { ElMessage.error(cause?.response?.data?.message || '告警关闭失败') }
}
function go(tab: string): void { router.push(`/records/${tab}`) }
function statusType(status: string): 'success' | 'warning' | 'danger' | 'info' { return status === 'SUCCEEDED' || status === 'CLOSED' || status === 'ok' ? 'success' : status === 'FAILED' || status === 'OPEN' || status === 'unavailable' ? 'danger' : 'warning' }
function formatDate(value?: string): string { return value ? new Date(value).toLocaleString() : '—' }
onMounted(load)
watch(moduleName, load)
</script>

<template>
  <section class="records-page">
    <div class="page-heading"><div><p class="eyebrow">运行可观测性</p><h1>{{ moduleName === 'audit' ? '审计记录' : '运行监控' }}</h1><p class="page-description">保留运行轨迹、错误、依赖健康和安全事件，告警可以追踪并关闭。</p></div><el-button :loading="loading" @click="load">刷新</el-button></div>
    <div class="records-tabs"><button v-for="tab in visibleTabs" :key="tab.key" :class="{ active: moduleName === tab.key }" @click="go(tab.key)">{{ tab.label }}</button></div>
    <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" />
    <template v-if="moduleName === 'runs' && store.can('agent:read')">
      <div v-if="overview" class="metric-grid"><el-card shadow="never"><span>请求数</span><strong>{{ overview.requests }}</strong></el-card><el-card shadow="never"><span>错误率</span><strong>{{ (overview.error_rate * 100).toFixed(1) }}%</strong></el-card><el-card shadow="never"><span>P95 延迟</span><strong>{{ overview.latency_ms.p95 }} ms</strong></el-card><el-card shadow="never"><span>开放告警</span><strong>{{ overview.active_alert_count }}</strong></el-card></div>
      <el-card v-if="overview" shadow="never" class="records-card"><template #header><span>依赖健康与告警</span></template><div class="dependency-list"><span v-for="(status, name) in overview.dependencies" :key="name"><b>{{ name }}</b><el-tag size="small" :type="statusType(status)">{{ status }}</el-tag></span></div><el-alert v-for="alert in overview.alerts.filter((item) => item.status === 'OPEN')" :key="alert.id" :title="alert.message" type="warning" show-icon class="alert-row"><template #default><span>{{ alert.code }} · {{ alert.id }}</span><el-button v-if="store.can('audit:write')" size="small" link type="primary" @click="closeAlert(alert.id)">关闭告警</el-button></template></el-alert></el-card>
      <el-card shadow="never" class="records-card"><template #header><span>Agent 运行</span></template><el-table v-loading="loading" :data="runs" empty-text="暂无运行记录"><el-table-column prop="id" label="运行 ID" min-width="190" /><el-table-column prop="agent_name" label="Agent" width="110" /><el-table-column prop="status" label="状态" width="110"><template #default="scope"><el-tag :type="statusType(scope.row.status)">{{ scope.row.status }}</el-tag></template></el-table-column><el-table-column prop="iterations" label="迭代" width="75" /><el-table-column label="Token" width="120"><template #default="scope">{{ scope.row.input_tokens + scope.row.output_tokens }}</template></el-table-column><el-table-column prop="stop_reason" label="停止原因" min-width="180" /><el-table-column label="耗时" width="110"><template #default="scope">{{ scope.row.duration_ms ?? '—' }} ms</template></el-table-column><el-table-column label="开始时间" min-width="170"><template #default="scope">{{ formatDate(scope.row.started_at) }}</template></el-table-column></el-table></el-card>
    </template>
    <el-card v-else-if="moduleName === 'audit' && store.can('audit:read')" shadow="never" class="records-card"><template #header><span>安全与业务审计（追加记录）</span></template><el-table v-loading="loading" :data="audits" empty-text="暂无审计记录"><el-table-column prop="event_type" label="事件" width="220" /><el-table-column prop="subject" label="用户" width="150" /><el-table-column prop="request_id" label="Request ID" min-width="190" /><el-table-column prop="trace_id" label="Trace ID" min-width="190" /><el-table-column label="时间" width="180"><template #default="scope">{{ formatDate(scope.row.occurred_at) }}</template></el-table-column><el-table-column label="详情" min-width="260"><template #default="scope"><pre>{{ JSON.stringify(scope.row.details || {}, null, 2) }}</pre></template></el-table-column></el-table></el-card>
  </section>
</template>

<style scoped>
.records-page { max-width: 1440px; margin: 0 auto; padding: 34px; }.records-tabs { display:flex; gap:8px; margin:24px 0; border-bottom:1px solid #dfe9e8; }.records-tabs button { border:0; border-bottom:2px solid transparent; background:transparent; padding:12px 16px; color:#718692; cursor:pointer; }.records-tabs button.active { border-bottom-color:#1e8a8a; color:#123f4b; font-weight:700; }.metric-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-bottom:16px; }.metric-grid span { display:block; color:#718692; font-size:12px; }.metric-grid strong { display:block; margin-top:10px; color:#123f4b; font-size:26px; }.records-card { margin-top:16px; }.dependency-list { display:flex; flex-wrap:wrap; gap:18px; }.dependency-list span { display:flex; align-items:center; gap:8px; }.alert-row { margin-top:12px; }.alert-row :deep(.el-alert__content) { width:100%; }.alert-row :deep(.el-alert__description) { display:flex; justify-content:space-between; }.records-card pre { max-height:100px; margin:0; overflow:auto; white-space:pre-wrap; font-size:11px; }@media (max-width: 900px) { .records-page { padding:20px; }.metric-grid { grid-template-columns:repeat(2,1fr); } }
</style>
