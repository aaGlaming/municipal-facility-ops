import { createRouter, createWebHistory } from 'vue-router'
import { useAppStore } from '../stores/app'
import AgentWorkspace from '../views/AgentWorkspace.vue'
import FacilityMap from '../views/FacilityMap.vue'
import LoginView from '../views/LoginView.vue'
import ModuleView from '../views/ModuleView.vue'
import WorkOrderView from '../views/WorkOrderView.vue'
import RagWorkbench from '../views/RagWorkbench.vue'
import RecordsView from '../views/RecordsView.vue'

const routes = [
  { path: '/', redirect: '/workspace' },
  { path: '/login', component: LoginView, meta: { public: true, title: '登录' } },
  { path: '/workspace', component: AgentWorkspace, meta: { title: '值守总览', permission: 'agent:run' } },
  { path: '/facilities', component: FacilityMap, meta: { title: '设施台账', permission: 'facility:read' } },
  { path: '/work-orders', component: WorkOrderView, meta: { title: '工单中心', permission: 'work_order:read', module: 'work-orders', state: 'ready' } },
  { path: '/agents/:module', component: ModuleView, meta: { title: 'Agent 工作台', permission: 'agent:run', module: 'agent' } },
  { path: '/rag', redirect: '/rag/documents' },
  { path: '/rag/:module', component: RagWorkbench, meta: { title: 'RAG 工作台', permission: 'document:read', module: 'rag' } },
  { path: '/records/:module', component: RecordsView, meta: { title: '运行与审计记录', module: 'records' } },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach(async (to) => {
  document.title = `${String(to.meta.title || '市政设施运维')} · 市政设施运维`
  if (to.meta.public) return true
  const store = useAppStore()
  if (!store.user.value) {
    const loaded = await store.loadCurrentUser()
    if (!loaded) return { path: '/login', query: { redirect: to.fullPath } }
  }
  const permission = to.meta.permission as string | undefined
  if (permission && !store.can(permission)) return { path: '/workspace' }
  return true
})

export default router
