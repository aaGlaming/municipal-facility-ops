<script setup lang="ts">
import { computed, onMounted, reactive, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '../api/client'
import { useAppStore } from '../stores/app'

interface DocumentRow { id: string; original_filename: string; status: string; error_reason?: string | null; facility_type?: string | null; region?: string | null; version: string; size_bytes: number; created_at: string }
interface ChunkRow { id: string; chunk_index: number; text: string; token_count: number; page_number?: number | null; heading?: string | null; cleaning_version: string }
interface SearchItem { chunk_id: string; document_id: string; document_name: string; page_number?: number | null; similarity: number; snippet: string; metadata: Record<string, unknown> }
interface SearchResponse { status: string; message?: string | null; query: string; rewritten_query: string; filters: Record<string, unknown>; items: SearchItem[]; warnings: string[] }

const route = useRoute()
const router = useRouter()
const store = useAppStore()
const moduleName = computed(() => String(route.params.module || 'documents'))
const documents = shallowRef<DocumentRow[]>([])
const chunks = shallowRef<ChunkRow[]>([])
const results = shallowRef<SearchResponse | null>(null)
const selectedDocument = shallowRef<DocumentRow | null>(null)
const selectedFile = shallowRef<File | null>(null)
const loading = shallowRef(false)
const uploading = shallowRef(false)
const error = shallowRef<string | null>(null)
const uploadForm = reactive({ region: '', facility_type: '', version: 'v1' })
const searchForm = reactive({ query: '', facility_type: '', region: '', version: '', top_k: 5, rerank: true })

const tabs = [
  { key: 'documents', label: '文档管理', permission: 'document:read' },
  { key: 'chunks', label: 'Chunk 预览', permission: 'document:read' },
  { key: 'embeddings', label: '向量入库', permission: 'document:embed' },
  { key: 'search', label: '检索调试', permission: 'document:read' },
]
const visibleTabs = computed(() => tabs.filter((tab) => store.can(tab.permission)))
const title = computed(() => ({ documents: '文档管理', chunks: 'Chunk 预览', embeddings: '向量入库', search: '检索调试' }[moduleName.value] || 'RAG 工作台'))

function selectFile(event: Event): void {
  selectedFile.value = (event.target as HTMLInputElement).files?.[0] || null
}
function go(tab: string): void { router.push(`/rag/${tab}`) }
async function loadDocuments(): Promise<void> {
  loading.value = true; error.value = null
  try { documents.value = (await api.get<{ items: DocumentRow[] }>('/api/rag/documents', { params: { page: 1, page_size: 50 } })).data.items } catch (cause: any) { error.value = cause?.response?.data?.message || '文档列表加载失败' } finally { loading.value = false }
}
async function upload(): Promise<void> {
  if (!selectedFile.value) { ElMessage.warning('请选择要上传的文档'); return }
  uploading.value = true; error.value = null
  const data = new FormData(); data.append('file', selectedFile.value); data.append('version', uploadForm.version); if (uploadForm.region) data.append('region', uploadForm.region); if (uploadForm.facility_type) data.append('facility_type', uploadForm.facility_type)
  try { await api.post('/api/rag/documents', data); ElMessage.success('文档已上传并解析'); selectedFile.value = null; await loadDocuments() } catch (cause: any) { error.value = cause?.response?.data?.message || '文档上传或解析失败' } finally { uploading.value = false }
}
function onDocumentChange(value: DocumentRow | undefined): void {
  if (value) void loadChunks(value)
}
async function loadChunks(document?: DocumentRow): Promise<void> {
  const target = document || selectedDocument.value || documents.value[0]
  if (!target) return
  selectedDocument.value = target; loading.value = true; error.value = null
  try { chunks.value = (await api.get<{ items: ChunkRow[] }>(`/api/rag/documents/${target.id}/chunks`)).data.items } catch (cause: any) { error.value = cause?.response?.data?.message || 'Chunk 加载失败' } finally { loading.value = false }
}
async function rebuild(document: DocumentRow): Promise<void> {
  loading.value = true; error.value = null
  try { await api.post(`/api/rag/documents/${document.id}/embeddings/rebuild`); ElMessage.success('Embedding 入库已提交'); await loadDocuments() } catch (cause: any) { error.value = cause?.response?.data?.message || '向量入库失败，请检查 Embedding 和 Chroma 服务' } finally { loading.value = false }
}
async function search(): Promise<void> {
  if (!searchForm.query.trim()) { ElMessage.warning('请输入检索词'); return }
  loading.value = true; error.value = null
  try { results.value = (await api.post<SearchResponse>('/api/rag/search/debug', { ...searchForm, facility_type: searchForm.facility_type || null, region: searchForm.region || null, version: searchForm.version || null })).data } catch (cause: any) { error.value = cause?.response?.data?.message || '检索失败，请检查向量服务或关键词索引' } finally { loading.value = false }
}
function formatBytes(size: number): string { return size < 1024 * 1024 ? `${Math.round(size / 1024)} KB` : `${(size / 1024 / 1024).toFixed(1)} MB` }
function statusType(status: string): 'success' | 'warning' | 'danger' | 'info' { return status === 'PARSED' || status === 'SUCCEEDED' ? 'success' : status === 'FAILED' || status === 'FAILED_RETRYABLE' ? 'danger' : status === 'UPLOADING' || status === 'RUNNING' ? 'warning' : 'info' }
onMounted(loadDocuments)
watch(moduleName, (value) => { if (value === 'documents' || value === 'chunks' || value === 'embeddings') loadDocuments() })
</script>

<template>
  <section class="rag-page">
    <div class="page-heading"><div><p class="eyebrow">知识与检索</p><h1>{{ title }}</h1><p class="page-description">文档、切块、向量和证据在一条可追溯链路里完成。</p></div><el-tag effect="plain" type="info">权限受控</el-tag></div>
    <div class="rag-tabs"><button v-for="tab in visibleTabs" :key="tab.key" :class="{ active: moduleName === tab.key }" @click="go(tab.key)">{{ tab.label }}</button></div>
    <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" class="rag-alert" />

    <template v-if="moduleName === 'documents'">
      <div class="rag-grid">
        <el-card shadow="never"><template #header><span>上传知识文档</span></template><el-form label-position="top"><el-form-item label="文件"><input class="file-input" type="file" accept=".pdf,.docx,.md,.markdown,.txt,.html,.htm" @change="selectFile" /></el-form-item><p v-if="selectedFile" class="selected-file">{{ selectedFile.name }} · {{ formatBytes(selectedFile.size) }}</p><el-form-item label="区域"><el-input v-model="uploadForm.region" placeholder="区域用户必须填写区域" /></el-form-item><el-form-item label="设施类型"><el-input v-model="uploadForm.facility_type" placeholder="例如 street_light" /></el-form-item><el-form-item label="版本"><el-input v-model="uploadForm.version" /></el-form-item><el-button type="primary" :loading="uploading" :disabled="!store.can('document:upload')" @click="upload">上传并解析</el-button></el-form></el-card>
        <el-card shadow="never"><template #header><span>处理链路</span></template><div class="pipeline"><div class="pipeline-step"><b>01</b><span>解析</span></div><div class="pipeline-line" /><div class="pipeline-step"><b>02</b><span>切块</span></div><div class="pipeline-line" /><div class="pipeline-step"><b>03</b><span>向量化</span></div></div><p class="pipeline-note">解析失败会保留错误原因；向量服务不可用时可先查看 Chunk 和关键词检索结果。</p></el-card>
      </div>
      <el-card shadow="never" class="table-card"><template #header><div class="card-heading"><span>文档列表</span><el-button link @click="loadDocuments">刷新</el-button></div></template><el-table v-loading="loading" :data="documents" row-key="id" empty-text="暂无文档"><el-table-column prop="original_filename" label="文档" min-width="220" /><el-table-column prop="status" label="解析状态" width="120"><template #default="scope"><el-tag :type="statusType(scope.row.status)">{{ scope.row.status }}</el-tag><p v-if="scope.row.error_reason" class="error-note">{{ scope.row.error_reason }}</p></template></el-table-column><el-table-column prop="region" label="区域" width="120" /><el-table-column prop="version" label="版本" width="90" /><el-table-column label="大小" width="100"><template #default="scope">{{ formatBytes(scope.row.size_bytes) }}</template></el-table-column><el-table-column label="操作" width="150"><template #default="scope"><el-button link type="primary" @click="loadChunks(scope.row)">查看 Chunk</el-button></template></el-table-column></el-table></el-card>
    </template>

    <template v-else-if="moduleName === 'chunks'">
      <el-card shadow="never" class="table-card"><template #header><div class="card-heading"><span>选择文档</span><el-button link @click="loadDocuments">刷新</el-button></div></template><el-select v-model="selectedDocument" value-key="id" placeholder="选择文档" class="document-select" @change="onDocumentChange"><el-option v-for="doc in documents" :key="doc.id" :label="`${doc.original_filename} · ${doc.version}`" :value="doc" /></el-select><el-table v-loading="loading" :data="chunks" class="chunk-table" empty-text="请选择已切块文档"><el-table-column prop="chunk_index" label="#" width="70" /><el-table-column prop="page_number" label="页码" width="80" /><el-table-column prop="heading" label="标题" width="180" /><el-table-column prop="token_count" label="Token" width="90" /><el-table-column prop="text" label="原文片段" min-width="420" show-overflow-tooltip /><el-table-column prop="id" label="Chunk ID" min-width="190" /></el-table></el-card>
    </template>

    <template v-else-if="moduleName === 'embeddings'">
      <el-card shadow="never" class="table-card"><template #header><span>Embedding 批次入口</span></template><el-table v-loading="loading" :data="documents" empty-text="暂无可入库文档"><el-table-column prop="original_filename" label="文档" min-width="250" /><el-table-column prop="status" label="解析状态" width="120"><template #default="scope"><el-tag :type="statusType(scope.row.status)">{{ scope.row.status }}</el-tag></template></el-table-column><el-table-column prop="version" label="版本" width="100" /><el-table-column label="操作" width="140"><template #default="scope"><el-button type="primary" link :disabled="!store.can('document:embed') || scope.row.status !== 'PARSED'" @click="rebuild(scope.row)">重建向量</el-button></template></el-table-column></el-table></el-card><el-alert title="实际向量化需要已配置 Embedding 端点和 Chroma 服务；失败时会保留可重试状态。" type="info" :closable="false" class="rag-alert" />
    </template>

    <template v-else>
      <el-card shadow="never" class="search-card"><el-form inline @submit.prevent="search"><el-form-item label="检索词"><el-input v-model="searchForm.query" class="query-input" placeholder="输入设施规范、维修步骤或安全要求" @keyup.enter="search" /></el-form-item><el-form-item label="设施类型"><el-input v-model="searchForm.facility_type" placeholder="可选" /></el-form-item><el-form-item label="区域"><el-input v-model="searchForm.region" placeholder="可选" /></el-form-item><el-form-item label="版本"><el-input v-model="searchForm.version" placeholder="可选" /></el-form-item><el-form-item label="Top-K"><el-input-number v-model="searchForm.top_k" :min="1" :max="50" /></el-form-item><el-form-item><el-checkbox v-model="searchForm.rerank">Rerank</el-checkbox></el-form-item><el-form-item><el-button type="primary" :loading="loading" @click="search">检索</el-button></el-form-item></el-form></el-card>
      <el-alert v-if="results?.warnings?.length" :title="results.warnings.join('；')" type="warning" show-icon :closable="false" class="rag-alert" /><el-alert v-if="results && !results.items.length" :title="results.message || '没有找到可用证据'" type="info" :closable="false" class="rag-alert" />
      <div v-if="results?.items.length" class="result-list"><el-card v-for="item in results.items" :key="item.chunk_id" shadow="never" class="result-card"><div class="result-head"><div><span class="result-score">{{ item.similarity.toFixed(3) }}</span><strong>{{ item.document_name }}</strong></div><el-tag size="small">页码 {{ item.page_number || '—' }}</el-tag></div><p class="snippet">{{ item.snippet }}</p><div class="result-meta"><span>Chunk ID：{{ item.chunk_id }}</span><span>文档 ID：{{ item.document_id }}</span><span>来源：{{ String(item.metadata.source_type || 'unknown') }}</span><span>版本：{{ String(item.metadata.version || '—') }}</span></div><el-collapse><el-collapse-item title="查看 metadata"><pre>{{ JSON.stringify(item.metadata, null, 2) }}</pre></el-collapse-item></el-collapse></el-card></div>
      <el-empty v-else-if="!loading && !results" description="输入查询词开始检索" />
    </template>
  </section>
</template>

<style scoped>
.rag-tabs { display: flex; flex-wrap: wrap; gap: 4px; margin: 0 0 20px; border-bottom: 1px solid #dbe5e8; }.rag-tabs button { padding: 11px 15px; border: 0; border-bottom: 2px solid transparent; color: #6f8492; background: transparent; font-size: 13px; }.rag-tabs button.active { color: #1e8a8a; border-bottom-color: #d89a36; font-weight: 700; }.rag-alert { margin: 16px 0; }.rag-grid { display: grid; grid-template-columns: minmax(0, .9fr) minmax(0, 1.1fr); gap: 18px; }.table-card, .search-card { margin-top: 18px; }.card-heading { display: flex; align-items: center; justify-content: space-between; }.file-input { width: 100%; padding: 10px; border: 1px dashed #bdcdd3; border-radius: 3px; background: #f7fafb; }.selected-file, .error-note { margin: -4px 0 14px; color: #1e8a8a; font-size: 12px; }.error-note { color: #c95f55; }.pipeline { display: flex; align-items: center; gap: 10px; margin: 15px 0; }.pipeline-step { display: grid; gap: 6px; color: #35506b; font-size: 12px; text-align: center; }.pipeline-step b { display: grid; place-items: center; width: 38px; height: 38px; color: #fff; background: #10273d; font-size: 12px; }.pipeline-line { flex: 1; height: 1px; background: #d89a36; }.pipeline-note { color: #718692; font-size: 13px; line-height: 1.6; }.document-select { width: min(100%, 520px); }.chunk-table { margin-top: 18px; }.search-card :deep(.el-form) { display: flex; flex-wrap: wrap; }.query-input { width: 320px; }.result-list { display: grid; gap: 14px; margin-top: 18px; }.result-card { border-left: 3px solid #1e8a8a; }.result-head, .result-head > div { display: flex; align-items: center; justify-content: space-between; gap: 12px; }.result-score { margin-right: 12px; color: #1e8a8a; font-family: monospace; font-weight: 800; }.snippet { margin: 16px 0; color: #35506b; line-height: 1.75; }.result-meta { display: flex; flex-wrap: wrap; gap: 8px 18px; color: #8296a0; font-family: monospace; font-size: 11px; }.result-card pre { max-height: 260px; overflow: auto; margin: 0; color: #35506b; font-size: 11px; white-space: pre-wrap; }
@media (max-width: 900px) { .rag-grid { grid-template-columns: 1fr; }.query-input { width: 100%; } }
</style>
