<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const moduleName = computed(() => String(route.params.module || 'work-orders'))
const moduleCopy: Record<string, { title: string; description: string; icon: string; state: string }> = {
  'work-orders': { title: '工单中心', description: '查看当前区域的维修队列、SLA 截止时间和状态转移。', icon: 'Tickets', state: 'ready' },
  triage: { title: '问题分诊', description: '从报修描述开始，判断类别、优先级并匹配设施候选。', icon: 'Filter', state: 'ready' },
  facility: { title: '设施识别', description: '核对设施台账、历史问题和低置信度候选。', icon: 'Aim', state: 'waiting' },
  sla: { title: 'SLA 判断', description: '解释优先级、首次响应窗口和解决截止时间。', icon: 'Timer', state: 'ready' },
  inspection: { title: '巡检计划', description: '安排巡检窗口，查看候选人员和安全确认。', icon: 'Calendar', state: 'ready' },
  dispatch: { title: '工单调度', description: '检查人员容量、巡检冲突和人工确认事项。', icon: 'Van', state: 'confirmation' },
  safety: { title: '安全作业', description: '生成隔离、PPE、围挡和交通防护清单。', icon: 'Warning', state: 'confirmation' },
  acceptance: { title: '维修验收', description: '核对维修证据、检查项和返工建议。', icon: 'CircleCheck', state: 'confirmation' },
  documents: { title: '文档管理', description: '上传、解析并管理用于 RAG 的知识文档。', icon: 'Document', state: 'ready' },
  chunks: { title: 'Chunk 预览', description: '查看清洗后的文本片段和来源定位。', icon: 'Files', state: 'ready' },
  embeddings: { title: '向量入库', description: '查看 Embedding 批次和 Chroma 入库状态。', icon: 'Cpu', state: 'loading' },
  search: { title: '检索调试', description: '查看召回结果、证据引用和原文片段。', icon: 'Search', state: 'ready' },
  runs: { title: '运行记录', description: '回看 Agent 运行轨迹、调用预算和停止原因。', icon: 'Operation', state: 'ready' },
  audit: { title: '审计记录', description: '追踪权限判断、工具调用和状态变更。', icon: 'Memo', state: 'ready' },
}
const current = computed(() => moduleCopy[moduleName.value] || moduleCopy['work-orders'])
const stateLabel = computed(() => ({ ready: '可开始', waiting: '等待输入', loading: '加载中', confirmation: '待人工确认' })[current.value.state])
</script>

<template>
  <section class="module-page">
    <div class="page-heading">
      <div><p class="eyebrow">{{ current.state === 'confirmation' ? '需要你的判断' : '工作模块' }}</p><h1>{{ current.title }}</h1><p class="page-description">{{ current.description }}</p></div>
      <el-tag :type="current.state === 'confirmation' ? 'warning' : current.state === 'loading' ? 'info' : 'success'" effect="dark">{{ stateLabel }}</el-tag>
    </div>
    <div class="module-grid">
      <el-card class="module-hero" shadow="never">
        <div class="module-icon"><el-icon><component :is="current.icon" /></el-icon></div>
        <div><h3>{{ current.title }}工作区</h3><p>这里将承载受权限保护的业务操作和证据。当前入口已经完成路由与状态边界，业务交互将在后续步骤接入。</p></div>
      </el-card>
      <el-card shadow="never"><template #header><span>状态边界</span></template><div class="state-list"><div><span class="dot success" />加载态</div><div><span class="dot warning" />待确认态</div><div><span class="dot danger" />失败态</div><div><span class="dot" />完成态</div></div></el-card>
    </div>
    <el-alert v-if="current.state === 'confirmation'" title="涉及高风险或不可逆动作时，系统只会提出建议，必须由授权人员确认后才能执行。" type="warning" show-icon :closable="false" />
    <el-empty v-else description="暂无需要处理的项目" />
  </section>
</template>
