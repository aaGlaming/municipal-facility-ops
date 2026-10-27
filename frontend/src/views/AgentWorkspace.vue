<script setup lang="ts">
import { computed, reactive, shallowRef } from 'vue'
import { ElMessage, ElMessageBox, type UploadFile } from 'element-plus'
import { api } from '../api/client'

interface AgentRecord {
  agent_run_id: string
  trace_id: string
  status: 'PENDING' | 'RUNNING' | 'WAITING_CONFIRMATION' | 'SUCCEEDED' | 'FAILED' | 'CANCELLED'
  phase: string
  created_at: string
  request: { intent: string; description: string; region?: string; attachments: Array<Record<string, unknown>> }
  response: { answer?: string; observations: Array<Record<string, any>>; pending_confirmation?: Record<string, any> | null; errors?: Array<Record<string, any>> }
  tool_trace: Array<Record<string, any>>
}

const form = reactive({ intent: '问题分诊与设施识别', description: '', region: '', session_id: `SESSION-${crypto.randomUUID().slice(0, 8)}` })
const attachments = shallowRef<UploadFile[]>([])
const run = shallowRef<AgentRecord | null>(null)
const loading = shallowRef(false)
const error = shallowRef<string | null>(null)
const phaseLabel = computed(() => ({ waiting_confirmation: '待人工确认', completed: '已完成', cancelled: '已取消', failed: '失败', running: '运行中' }[run.value?.phase || ''] || '待提交'))
const statusType = computed(() => run.value?.status === 'WAITING_CONFIRMATION' ? 'warning' : run.value?.status === 'SUCCEEDED' ? 'success' : run.value?.status === 'FAILED' ? 'danger' : 'info')

function onFileChange(file: UploadFile): void {
  attachments.value = [...attachments.value, file].slice(-5)
}
function removeFile(file: UploadFile): void {
  attachments.value = attachments.value.filter((item) => item.uid !== file.uid)
}
async function submitRun(): Promise<void> {
  if (!form.description.trim() || !form.region.trim()) {
    ElMessage.warning('请填写问题描述和区域')
    return
  }
  loading.value = true
  error.value = null
  try {
    const { data } = await api.post<AgentRecord>('/api/agents/runs', { ...form, attachments: attachments.value.map((file) => ({ name: file.name, size: file.size, type: file.raw?.type })) })
    run.value = data
  } catch (cause: any) {
    error.value = cause?.response?.data?.message || '运行启动失败，请检查 API 和权限'
  } finally {
    loading.value = false
  }
}
async function decide(decision: 'approve' | 'reject'): Promise<void> {
  if (!run.value) return
  if (decision === 'reject') {
    await ElMessageBox.confirm('拒绝后本次运行会停止，是否继续？', '拒绝高风险动作', { type: 'warning' })
  }
  loading.value = true
  try {
    const { data } = await api.post<AgentRecord>(`/api/agents/runs/${run.value.agent_run_id}/confirmation`, { decision, reason: decision === 'approve' ? '授权人员确认' : '授权人员拒绝' })
    run.value = data
  } catch (cause: any) {
    error.value = cause?.response?.data?.message || '确认操作失败'
  } finally {
    loading.value = false
  }
}
async function cancelRun(): Promise<void> {
  if (!run.value) return
  loading.value = true
  try { run.value = (await api.post<AgentRecord>(`/api/agents/runs/${run.value.agent_run_id}/cancel`, { reason: '用户取消运行' })).data } catch { error.value = '取消失败' } finally { loading.value = false }
}
async function retryRun(): Promise<void> {
  if (!run.value) return
  loading.value = true
  try { run.value = (await api.post<AgentRecord>(`/api/agents/runs/${run.value.agent_run_id}/retry`)).data } catch { error.value = '重试失败' } finally { loading.value = false }
}
</script>

<template>
  <section class="workspace-page">
    <div class="page-heading"><div><p class="eyebrow">Agent 值守台</p><h1>把现场问题交给流程</h1><p class="page-description">输入报修事实，系统会保留运行阶段、工具轨迹、证据和每次人工确认。</p></div><el-tag v-if="run" :type="statusType" effect="dark">{{ phaseLabel }}</el-tag></div>
    <div class="workspace-grid">
      <el-card class="report-card" shadow="never">
        <template #header><div class="card-heading"><span>发起一次运行</span><span class="trace-note">每次运行独立生成 trace_id</span></div></template>
        <el-form label-position="top">
          <el-form-item label="处理意图"><el-select v-model="form.intent" class="full-width"><el-option label="问题分诊与设施识别" value="问题分诊与设施识别" /><el-option label="高风险安全作业" value="安全作业审批" /><el-option label="工单调度" value="工单调度" /><el-option label="维修验收" value="维修验收" /></el-select></el-form-item>
          <el-form-item label="问题描述"><el-input v-model="form.description" type="textarea" :rows="5" maxlength="5000" show-word-limit placeholder="例如：中心区人民路路灯不亮，影响夜间通行。" /></el-form-item>
          <el-form-item label="区域"><el-input v-model="form.region" placeholder="例如：中心区" /></el-form-item>
          <el-form-item label="附件（最多 5 个文件名）"><el-upload :auto-upload="false" :show-file-list="true" :limit="5" @change="onFileChange" @remove="removeFile"><el-button plain>选择现场照片或文件</el-button></el-upload></el-form-item>
          <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" />
          <el-button class="primary-action" type="primary" :loading="loading" @click="submitRun">开始 Agent 运行</el-button>
        </el-form>
      </el-card>
      <el-card class="run-card" shadow="never">
        <template #header><div class="card-heading"><span>运行轨迹</span><span v-if="run" class="trace-id">{{ run.trace_id }}</span></div></template>
        <el-empty v-if="!run" description="提交报修后，这里会显示运行阶段" />
        <template v-else>
          <div class="run-meta"><span>运行 ID <b>{{ run.agent_run_id }}</b></span><el-tag size="small" :type="statusType">{{ run.status }}</el-tag></div>
          <el-timeline>
            <el-timeline-item v-for="(item, index) in run.response.observations" :key="`${item.observation_id || index}`" :timestamp="String(item.created_at || '')" placement="top"><strong>{{ item.summary }}</strong><p v-if="item.data">{{ item.data.phase || item.data.decision || '' }}</p></el-timeline-item>
          </el-timeline>
          <el-alert v-if="run.response.pending_confirmation" title="需要人工确认" type="warning" show-icon :closable="false"><p>{{ run.response.pending_confirmation.summary }}</p><div class="confirm-actions"><el-button type="warning" @click="decide('approve')">确认执行</el-button><el-button plain @click="decide('reject')">拒绝</el-button></div></el-alert>
          <div v-if="run.response.answer" class="answer-block"><span>最终建议</span><p>{{ run.response.answer }}</p></div>
          <div v-if="run.tool_trace.length" class="tool-trace"><span>工具轨迹</span><div v-for="event in run.tool_trace" :key="`${event.created_at}-${event.type}`">{{ event.type }} · {{ event.decision || event.tool_name || '' }}</div></div>
          <div class="run-actions"><el-button v-if="['PENDING', 'RUNNING', 'WAITING_CONFIRMATION'].includes(run.status)" text type="danger" @click="cancelRun">取消运行</el-button><el-button v-if="['FAILED', 'CANCELLED'].includes(run.status)" text type="primary" @click="retryRun">重试</el-button></div>
        </template>
      </el-card>
    </div>
  </section>
</template>

<style scoped>
.workspace-grid { display: grid; grid-template-columns: minmax(0, 1.05fr) minmax(360px, .95fr); gap: 20px; }
.card-heading, .run-meta, .run-actions { display: flex; align-items: center; justify-content: space-between; gap: 12px; }.trace-note { color: #8aa0ac; font-size: 12px; }.trace-id { max-width: 220px; overflow: hidden; color: #1e8a8a; font-family: monospace; font-size: 11px; text-overflow: ellipsis; }.full-width { width: 100%; }.primary-action { width: 100%; margin-top: 20px; }.run-meta { margin-bottom: 24px; color: #718692; font-size: 12px; }.run-meta b { color: #12253a; }.confirm-actions { display: flex; gap: 8px; margin-top: 12px; }.answer-block, .tool-trace { margin-top: 20px; padding: 14px; background: #f5f8f8; color: #35506b; font-size: 13px; line-height: 1.6; }.answer-block span, .tool-trace > span { color: #1e8a8a; font-size: 11px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; }.answer-block p { margin: 8px 0 0; }.tool-trace div { padding-top: 7px; font-family: monospace; font-size: 11px; }
@media (max-width: 980px) { .workspace-grid { grid-template-columns: 1fr; } }
</style>
