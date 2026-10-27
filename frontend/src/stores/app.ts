import { computed, reactive, readonly } from 'vue'
import { api } from '../api/client'
import type { CurrentUser, MenuItem } from '../types/domain'

const state = reactive<{
  token: string | null
  user: CurrentUser | null
  authLoading: boolean
  authError: string | null
}>({ token: null, user: null, authLoading: false, authError: null })

const menuItems: MenuItem[] = [
  { label: '值守总览', path: '/workspace', group: 'core', icon: 'Odometer', description: 'Agent 运行、待确认和今日值守概览' },
  { label: '设施台账', path: '/facilities', group: 'core', permission: 'facility:read', icon: 'OfficeBuilding', description: '设施位置、状态和问题历史' },
  { label: '工单中心', path: '/work-orders', group: 'core', permission: 'work_order:read', icon: 'Tickets', description: '工单状态、SLA 和维修进度' },
  { label: '问题分诊', path: '/agents/triage', group: 'agent', permission: 'agent:run', icon: 'Filter', description: '类别判断、设施匹配和重复报修' },
  { label: '设施识别', path: '/agents/facility', group: 'agent', permission: 'agent:run', icon: 'Aim', description: '候选设施与历史关联' },
  { label: 'SLA 判断', path: '/agents/sla', group: 'agent', permission: 'agent:run', icon: 'Timer', description: '优先级、截止时间和升级建议' },
  { label: '巡检计划', path: '/agents/inspection', group: 'agent', permission: 'agent:run', icon: 'Calendar', description: '巡检窗口和人员候选' },
  { label: '工单调度', path: '/agents/dispatch', group: 'agent', permission: 'agent:run', icon: 'Van', description: '容量、冲突和派工建议' },
  { label: '安全作业', path: '/agents/safety', group: 'agent', permission: 'agent:run', icon: 'Warning', description: '隔离、PPE 和交通防护清单' },
  { label: '维修验收', path: '/agents/acceptance', group: 'agent', permission: 'agent:run', icon: 'CircleCheck', description: '证据核验、通过或返工建议' },
  { label: '文档管理', path: '/rag/documents', group: 'rag', permission: 'document:read', icon: 'Document', description: '上传和解析知识文档' },
  { label: 'Chunk 预览', path: '/rag/chunks', group: 'rag', permission: 'document:read', icon: 'Files', description: '查看清洗后的文本分块' },
  { label: '向量入库', path: '/rag/embeddings', group: 'rag', permission: 'document:write', icon: 'Cpu', description: 'Embedding 批次和 Chroma 状态' },
  { label: '检索调试', path: '/rag/search', group: 'rag', permission: 'document:read', icon: 'Search', description: '召回、证据和原文片段' },
  { label: '运行记录', path: '/records/runs', group: 'records', permission: 'agent:read', icon: 'Operation', description: 'Agent 运行轨迹和停止原因' },
  { label: '审计记录', path: '/records/audit', group: 'records', permission: 'audit:read', icon: 'Memo', description: '权限、工具和状态变更审计' },
]

function can(permission?: string): boolean {
  if (!permission) return true
  const permissions = state.user?.permissions || []
  return permissions.includes('*') || permissions.includes('admin:*') || permissions.includes(permission)
}

export function useAppStore() {
  const visibleMenus = computed(() => menuItems.filter((item) => can(item.permission)))
  const menuGroups = computed(() => ({
    core: visibleMenus.value.filter((item) => item.group === 'core'),
    agent: visibleMenus.value.filter((item) => item.group === 'agent'),
    rag: visibleMenus.value.filter((item) => item.group === 'rag'),
    records: visibleMenus.value.filter((item) => item.group === 'records'),
  }))

  async function login(username: string, password: string): Promise<void> {
    state.authLoading = true
    state.authError = null
    try {
      const { data } = await api.post<{ access_token: string }>('/api/auth/login', { username, password })
      state.token = data.access_token
      await loadCurrentUser()
    } catch (error: any) {
      state.token = null
      state.user = null
      state.authError = error?.response?.data?.message || error?.response?.data?.detail?.message || '登录失败，请检查账号和服务状态'
      throw error
    } finally {
      state.authLoading = false
    }
  }

  async function loadCurrentUser(): Promise<boolean> {
    if (!state.token) return false
    state.authLoading = true
    try {
      const { data } = await api.get<CurrentUser>('/api/auth/me')
      state.user = data
      return true
    } catch {
      clearSession()
      return false
    } finally {
      state.authLoading = false
    }
  }

  function clearSession(): void {
    state.token = null
    state.user = null
    state.authError = null
  }

  return { state: readonly(state), token: computed(() => state.token), user: computed(() => state.user), authLoading: computed(() => state.authLoading), authError: computed(() => state.authError), visibleMenus, menuGroups, menuItems, can, login, loadCurrentUser, clearSession }
}

export function getAccessToken(): string | null {
  return state.token
}
