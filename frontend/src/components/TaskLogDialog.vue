<template>
  <el-dialog
    v-model="visible"
    :title="title"
    width="760px"
    class="task-log-dialog"
    :close-on-click-modal="false"
  >
    <div v-loading="loading" class="log-body">
      <el-empty v-if="!loading && entries.length === 0" description="暂无执行日志" :image-size="80" />
      <div v-else class="log-list">
        <article v-for="(entry, index) in entries" :key="index" class="log-entry">
          <header class="log-meta">
            <span class="status-pill" :data-tone="levelTone(entry.level)">{{ entry.level || 'INFO' }}</span>
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
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getTaskLogs } from '../api/task'

const visible = ref(false)
const loading = ref(false)
const task = ref(null)
const entries = ref([])

const title = computed(() => {
  if (!task.value) return '任务日志'
  return `任务日志 #${task.value.id}`
})

async function open(row) {
  task.value = row
  visible.value = true
  loading.value = true
  entries.value = []
  try {
    const { data } = await getTaskLogs(row.id)
    entries.value = data.data.items || []
  } catch (err) {
    ElMessage.error(err.response?.data?.message || '加载任务日志失败')
  } finally {
    loading.value = false
  }
}

function levelTone(level) {
  const map = { INFO: 'progress', WARN: 'warning', ERROR: 'danger', DEBUG: 'neutral' }
  return map[level] ?? 'progress'
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

.status-pill {
  display: inline-flex;
  align-items: center;
  padding: 2px var(--space-5);
  border-radius: var(--radius-full);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  background: var(--badge-bg-neutral);
  color: var(--badge-fg-neutral);
  border: 1px solid transparent;
  white-space: nowrap;
}
.status-pill[data-tone='progress'] {
  background: var(--color-info-bg);
  color: var(--color-info-fg);
  border-color: var(--color-info-border);
}
.status-pill[data-tone='warning'] {
  background: var(--color-warning-bg);
  color: var(--color-warning-fg);
  border-color: var(--color-warning-border);
}
.status-pill[data-tone='danger'] {
  background: var(--color-danger-bg);
  color: var(--color-danger-fg);
  border-color: var(--color-danger-border);
}
</style>
