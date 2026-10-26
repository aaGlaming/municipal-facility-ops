<script setup lang="ts">
const menus = [
  { label: 'Agent 工作台', path: '/workspace' },
  { label: '设施地图', path: '/facilities' },
  { label: 'RAG 工作台', path: '/rag' },
]
</script>

<template>
  <el-container class="layout">
    <el-aside width="240px">
      <h1>市政设施运维</h1>
      <el-menu router :default-active="$route.path">
        <el-menu-item v-for="menu in menus" :key="menu.path" :index="menu.path">{{ menu.label }}</el-menu-item>
      </el-menu>
    </el-aside>
    <el-main><router-view /></el-main>
  </el-container>
</template>

<style>
html, body, #app { margin: 0; min-height: 100%; font-family: Inter, "Microsoft YaHei", sans-serif; }
.layout { min-height: 100vh; background: #f5f7fa; }
aside { background: #182230; color: white; padding-top: 20px; }
aside h1 { padding: 0 20px; font-size: 20px; }
.el-menu { border-right: 0; background: transparent; }
.el-menu-item { color: #cbd5e1; }
.el-menu-item.is-active { color: #fff; background: #2563eb; }
</style>
