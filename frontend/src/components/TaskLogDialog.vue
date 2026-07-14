<template>
  <el-dialog
    :model-value="visible"
    :title="title"
    width="760px"
    class="task-log-dialog"
    :close-on-click-modal="false"
    @update:model-value="onVisibleChange"
    @open="onOpen"
  >
    <div class="log-toolbar">
      <el-radio-group v-model="levelFilter" size="small">
        <el-radio-button value="ALL">全部</el-radio-button>
        <el-radio-button value="INFO">信息</el-radio-button>
        <el-radio-button value="WARN">警告</el-radio-button>
        <el-radio-button value="ERROR">错误</el-radio-button>
      </el-radio-group>
      <div class="log-toolbar__right">
        <span class="t-caption">{{ filteredEntries.length }} 条</span>
        <el-button size="small" :loading="loading" @click="refresh">刷新</el-button>
      </div>
    </div>

    <div v-loading="loading" class="log-body">
      <el-empty v-if="!loading && filteredEntries.length === 0" description="暂无执行日志" :image-size="80" />
      <div v-else class="log-list">
        <article v-for="(entry, index) in filteredEntries" :key="index" class="log-entry">
          <header class="log-meta">
            <StatusPill :tone="levelTone(entry.level)" :label="entry.level || 'INFO'" />
            <span class="t-mono">{{ formatTime(entry.ts) }}</span>
            <span class="t-caption">{{ entry.step || '—' }}</span>
            <span class="t-caption">{{ entry.event || '—' }}</span>
            <span class="t-mono">{{ entry.elapsed_ms ?? 0 }}ms</span>
          </header>
          <div class="log-msg">{{ entry.msg || '—' }}</div>
          <pre v-if="entry.data && Object.keys(entry.data).length">{{ formatJson(entry.data) }}</pre>
        </article>
      </div>
    </div>
  </el-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getTaskLogs } from '../api/task'
import StatusPill from './StatusPill.vue'

// 支持两种调用方式：
//   1) v-model:visible + :task-id（BenchmarkManagement 用）
//   2) ref + open(row)（RedTeamManagement 用，向后兼容）
const props = defineProps({
  visible: { type: Boolean, default: false },
  taskId: { type: [Number, String], default: null },
})
const emit = defineEmits(['update:visible'])

const loading = ref(false)
const entries = ref([])
const levelFilter = ref('ALL')
const internalTaskId = ref(null)   // 兼容 open(row) 方式

const activeTaskId = computed(() => internalTaskId.value ?? props.taskId)

const title = computed(() =>
  activeTaskId.value ? `任务日志 #${activeTaskId.value}` : '任务日志',
)

const filteredEntries = computed(() => {
  if (levelFilter.value === 'ALL') return entries.value
  return entries.value.filter((e) => (e.level || 'INFO') === levelFilter.value)
})

// 方式 1：监听 visible + taskId
watch(
  () => [props.visible, props.taskId],
  ([vis, tid]) => {
    if (vis && tid != null) {
      internalTaskId.value = null
      fetchLogs(tid)
    }
  },
)

// 方式 2：ref 调用
function open(row) {
  internalTaskId.value = row.id
  entries.value = []
  fetchLogs(row.id)
  // 无 v-model 时靠内部 visible；这里通过 emit 也能兼容
  emit('update:visible', true)
}

function onVisibleChange(v) {
  emit('update:visible', v)
}

function onOpen() {
  if (activeTaskId.value != null) fetchLogs(activeTaskId.value)
}

async function refresh() {
  if (activeTaskId.value != null) fetchLogs(activeTaskId.value)
}

async function fetchLogs(id) {
  loading.value = true
  try {
    const { data } = await getTaskLogs(id)
    entries.value = data.data.items || []
  } catch (err) {
    ElMessage.error(err.response?.data?.message || '加载任务日志失败')
  } finally {
    loading.value = false
  }
}

function levelTone(level) {
  const map = { INFO: 'info', WARN: 'warning', ERROR: 'danger', DEBUG: 'neutral' }
  return map[level] ?? 'info'
}

function formatTime(value) {
  return value ? new Date(value).toLocaleString('zh-CN') : '—'
}

function formatJson(value) {
  return JSON.stringify(value, null, 2)
}

defineExpose({ open })
</script>

<style scoped>
.log-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-5);
  margin-bottom: var(--space-5);
}
.log-toolbar__right {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  color: var(--fg-tertiary);
}
.log-body { min-height: 220px; max-height: 62vh; overflow: auto; }
.log-list { display: flex; flex-direction: column; gap: var(--space-5); }
.log-entry {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: var(--space-5) var(--space-6);
  background: var(--bg-surface-sunken);
}
.log-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-5);
  align-items: center;
  color: var(--fg-secondary);
  margin-bottom: var(--space-3);
}
.log-msg {
  color: var(--fg-primary);
  font-size: var(--text-sm);
  line-height: var(--leading-relaxed);
}
pre {
  margin: var(--space-3) 0 0;
  max-height: 180px;
  overflow: auto;
  padding: var(--space-5);
  border-radius: var(--radius-sm);
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  color: var(--fg-primary);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: var(--leading-normal);
}
</style>
