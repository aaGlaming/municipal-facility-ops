<script setup lang="ts">
import { computed, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAppStore } from '../stores/app'

const route = useRoute()
const router = useRouter()
const store = useAppStore()
const form = reactive({ username: '', password: '' })
const redirect = computed(() => typeof route.query.redirect === 'string' ? route.query.redirect : '/workspace')

async function submit(): Promise<void> {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入账号和密码')
    return
  }
  try {
    await store.login(form.username, form.password)
    await router.replace(redirect.value)
  } catch {
    // Error text is rendered below so the form remains actionable.
  }
}
</script>

<template>
  <main class="login-page">
    <section class="login-visual">
      <div class="visual-grid" />
      <div class="visual-copy">
        <div class="brand-mark large">M</div>
        <p class="eyebrow">MUNICIPAL OPERATIONS CONTROL</p>
        <h1>让每一处设施，<br /><em>都有回应。</em></h1>
        <p class="visual-note">从问题分诊到维修验收，统一记录每一次判断、动作与证据。</p>
      </div>
      <div class="visual-footer">城市设施 · 数据驱动 · 全程可追溯</div>
    </section>
    <section class="login-panel">
      <div class="login-card">
        <p class="eyebrow">值守人员入口</p>
        <h2>欢迎回来</h2>
        <p class="muted">登录后进入你的区域运维工作台。</p>
        <el-form label-position="top" @submit.prevent="submit">
          <el-form-item label="账号"><el-input v-model="form.username" size="large" autocomplete="username" placeholder="输入工作账号" /></el-form-item>
          <el-form-item label="密码"><el-input v-model="form.password" size="large" type="password" show-password autocomplete="current-password" placeholder="输入密码" @keyup.enter="submit" /></el-form-item>
          <el-alert v-if="store.authError.value" :title="store.authError.value" type="error" :closable="false" show-icon />
          <el-button class="login-button" size="large" type="primary" :loading="store.authLoading.value" @click="submit">进入工作台</el-button>
        </el-form>
        <p class="login-hint">账号权限和区域范围由平台认证服务决定。</p>
      </div>
    </section>
  </main>
</template>
