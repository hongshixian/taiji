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
        <div v-for="(entry, index) in entries" :key="index" class="log-entry">
          <div class="log-meta">
            <el-tag :type="levelType(entry.level)" size="small">{{ entry.level || 'INFO' }}</el-tag>
            <span>{{ formatTime(entry.ts) }}</span>
            <span>{{ entry.step || '-' }}</span>
            <span>{{ entry.event || '-' }}</span>
            <span>{{ entry.elapsed_ms ?? 0 }}ms</span>
          </div>
          <div class="log-msg">{{ entry.msg || '-' }}</div>
          <pre v-if="entry.data && Object.keys(entry.data).length">{{ formatJson(entry.data) }}</pre>
        </div>
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

function levelType(level) {
  const map = { INFO: 'info', WARN: 'warning', ERROR: 'danger', DEBUG: '' }
  return map[level] ?? 'info'
}

function formatTime(value) {
  return value ? new Date(value).toLocaleString('zh-CN') : '-'
}

function formatJson(value) {
  return JSON.stringify(value, null, 2)
}

defineExpose({ open })
</script>

<style scoped>
.log-body { min-height: 220px; max-height: 62vh; overflow: auto; }
.log-list { display: flex; flex-direction: column; gap: 10px; }
.log-entry {
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
  padding: 10px 12px;
  background: var(--el-fill-color-lighter);
}
.log-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  margin-bottom: 6px;
}
.log-msg { color: var(--el-text-color-primary); font-size: 13px; line-height: 1.5; }
pre {
  margin: 8px 0 0;
  max-height: 180px;
  overflow: auto;
  padding: 8px;
  border-radius: 6px;
  background: var(--el-fill-color);
  color: var(--el-text-color-regular);
  font-size: 12px;
  line-height: 1.45;
}
</style>
