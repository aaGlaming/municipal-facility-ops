<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from './stores/app'
import type { MenuItem } from './types/domain'

const route = useRoute()
const router = useRouter()
const store = useAppStore()
const collapsed = ref(false)
const mobileOpen = ref(false)

const groupLabels = { core: '值守中心', agent: 'Agent 编排', rag: '知识与检索', records: '可追溯记录' } as const
const groups = computed(() => Object.entries(store.menuGroups.value) as [keyof typeof groupLabels, MenuItem[]][])
const activeMenu = computed(() => route.path)

function navigate(path: string): void {
  mobileOpen.value = false
  router.push(path)
}
function logout(): void {
  store.clearSession()
  router.push('/login')
}
</script>

<template>
  <div class="app-shell" :class="{ 'is-collapsed': collapsed, 'mobile-open': mobileOpen }">
    <div v-if="mobileOpen" class="mobile-scrim" aria-hidden="true" @click="mobileOpen = false" />
    <aside class="sidebar">
      <div class="brand-block">
        <div class="brand-mark">M</div>
        <div v-if="!collapsed" class="brand-copy">
          <strong>Municipal Ops</strong>
          <span>市政设施运维台</span>
        </div>
        <button class="collapse-button" :aria-label="collapsed ? '展开菜单' : '收起菜单'" @click="collapsed = !collapsed">{{ collapsed ? '›' : '‹' }}</button>
      </div>
      <nav class="side-nav" aria-label="主导航">
        <template v-for="[group, items] in groups" :key="group">
          <p v-if="!collapsed" class="nav-label">{{ groupLabels[group] }}</p>
          <button v-for="item in items" :key="item.path" class="nav-item" :class="{ active: activeMenu === item.path || route.path.startsWith(`${item.path}/`) }" :title="collapsed ? item.label : item.description" @click="navigate(item.path)">
            <el-icon><component :is="item.icon" /></el-icon>
            <span v-if="!collapsed">{{ item.label }}</span>
          </button>
        </template>
      </nav>
      <div v-if="!collapsed" class="sidebar-foot">运行环境 · {{ store.user.value?.regions?.join(' / ') || '未登录' }}</div>
    </aside>

    <main class="main-shell">
      <header class="topbar">
        <button class="menu-toggle" aria-label="打开菜单" @click="mobileOpen = true"><el-icon><Menu /></el-icon></button>
        <div class="breadcrumb"><span>市政设施运维</span><b>/</b><strong>{{ route.meta.title || '工作台' }}</strong></div>
        <div class="top-actions">
          <el-tag v-if="store.user.value" effect="plain" type="info">{{ store.user.value.roles.join(' · ') }}</el-tag>
          <el-button v-if="store.user.value" link @click="logout">退出登录</el-button>
        </div>
      </header>
      <section class="content-area"><router-view /></section>
    </main>
  </div>
</template>
