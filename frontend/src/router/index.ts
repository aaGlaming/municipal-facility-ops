import { createRouter, createWebHistory } from 'vue-router'
import AgentWorkspace from '../views/AgentWorkspace.vue'
import FacilityMap from '../views/FacilityMap.vue'
import RagWorkbench from '../views/RagWorkbench.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/workspace' },
    { path: '/workspace', component: AgentWorkspace },
    { path: '/facilities', component: FacilityMap },
    { path: '/rag', component: RagWorkbench },
  ],
})
