<template>
  <div class="dashboard">
    <h1>☯ 太极 · 网页分析</h1>
    <p class="subtitle">输入一个 URL，异步分析网页标题、摘要和关键词</p>

    <div class="input-row">
      <el-input
        v-model="url"
        placeholder="输入网页 URL，如 https://example.com"
        size="large"
        class="url-input"
        @keyup.enter="handleSubmit"
      />
      <el-button
        type="primary"
        size="large"
        :loading="submitting"
        @click="handleSubmit"
      >
        开始分析
      </el-button>
    </div>

    <!-- 任务卡片列表 -->
    <div
      v-for="task in taskList"
      :key="task.id"
      class="result-card"
    >
      <el-card>
        <template #header>
          <div class="card-header">
            <span class="card-url">{{ task.url }}</span>
            <el-tag :type="statusTag(task.frontendStatus)" size="small">
              {{ statusLabel(task.frontendStatus) }}
            </el-tag>
          </div>
        </template>

        <!-- submitting / pending / running -->
        <el-skeleton
          v-if="['submitting', 'pending', 'running'].includes(task.frontendStatus)"
          :rows="4"
          animated
        />
        <div
          v-if="['pending', 'running'].includes(task.frontendStatus)"
          class="elapsed-time"
        >
          已等待 {{ task.elapsed }} 秒
        </div>

        <!-- success -->
        <template v-else-if="task.frontendStatus === 'success'">
          <div class="result-item">
            <strong>标题：</strong>{{ task.title }}
          </div>
          <div class="result-item">
            <strong>摘要：</strong>
            <p class="summary-text">{{ task.summary }}</p>
          </div>
          <div v-if="task.keywords?.length" class="result-item">
            <strong>关键词：</strong>
            <el-tag
              v-for="kw in task.keywords"
              :key="kw"
              class="keyword-tag"
              size="small"
            >
              {{ kw }}
            </el-tag>
          </div>
          <div class="result-meta">
            分析完成于 {{ formatTime(task.completed_at) }}
          </div>
        </template>

        <!-- submit_failed -->
        <el-alert
          v-else-if="task.frontendStatus === 'submit_failed'"
          title="提交失败"
          :description="task.error"
          type="error"
          show-icon
          :closable="false"
        >
          <template #default>
            <el-button size="small" type="primary" @click="retrySubmit(task)"
              >重新提交</el-button
            >
            <el-button size="small" @click="removeTask(task.id)">关闭</el-button>
          </template>
        </el-alert>

        <!-- failed -->
        <el-alert
          v-else-if="task.frontendStatus === 'failed'"
          title="分析失败"
          :description="task.error_message"
          type="error"
          show-icon
          :closable="false"
        >
          <template #default>
            <el-button size="small" type="primary" :loading="task.retrying" @click="retryTask(task)"
              >重新分析</el-button
            >
            <el-button size="small" @click="removeTask(task.id)">关闭</el-button>
          </template>
        </el-alert>

        <!-- timeout -->
        <el-alert
          v-else-if="task.frontendStatus === 'timeout'"
          title="分析超时"
          description="任务超过 60 秒未完成，Worker 可能异常"
          type="warning"
          show-icon
          :closable="false"
        >
          <template #default>
            <el-button size="small" type="primary" :loading="task.retrying" @click="retryTask(task)"
              >重新分析</el-button
            >
            <el-button size="small" @click="removeTask(task.id)">关闭</el-button>
          </template>
        </el-alert>

        <!-- not_found -->
        <el-alert
          v-else-if="task.frontendStatus === 'not_found'"
          title="任务丢失"
          description="无法找到该任务，Celery Worker 可能崩溃"
          type="warning"
          show-icon
          :closable="false"
        >
          <template #default>
            <el-button size="small" type="primary" :loading="task.retrying" @click="retryTask(task)"
              >重新分析</el-button
            >
            <el-button size="small" @click="removeTask(task.id)">关闭</el-button>
          </template>
        </el-alert>

        <!-- query_error -->
        <el-alert
          v-else-if="task.frontendStatus === 'query_error'"
          title="查询失败"
          description="网络异常，正在自动重试..."
          type="info"
          show-icon
          :closable="false"
        >
          <template #default>
            <el-button size="small" @click="removeTask(task.id)">关闭</el-button>
          </template>
        </el-alert>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { submitAnalysis, getAnalysis, retryAnalysis } from '../api/analyze'

const MAX_POLLS = 30 // 60 秒（2s * 30）
const url = ref('')
const submitting = ref(false)
const taskList = ref([]) // { id, url, frontendStatus, pollCount, pollTimer, elapsed, elapsedTimer, retrying, ... }

const statusLabel = (s) => {
  const map = {
    submitting: '提交中',
    submit_failed: '提交失败',
    pending: '排队中',
    running: '分析中',
    success: '已完成',
    failed: '失败',
    timeout: '超时',
    not_found: '任务丢失',
    query_error: '查询异常',
  }
  return map[s] || s
}

const statusTag = (s) => {
  const map = {
    submitting: 'info',
    submit_failed: 'danger',
    pending: 'info',
    running: 'warning',
    success: 'success',
    failed: 'danger',
    timeout: 'warning',
    not_found: 'warning',
    query_error: 'info',
  }
  return map[s] || 'info'
}

function formatTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('zh-CN')
}

// ─── 提交 ──────────────────────────────────────

async function handleSubmit() {
  const trimmed = url.value.trim()
  if (!trimmed) return ElMessage.warning('请输入 URL')
  if (!trimmed.startsWith('http://') && !trimmed.startsWith('https://'))
    return ElMessage.warning('URL 必须以 http:// 或 https:// 开头')

  const taskId = Date.now() // 临时 ID（提交前）
  const task = {
    id: taskId,
    url: trimmed,
    frontendStatus: 'submitting',
    pollCount: 0,
    pollTimer: null,
    elapsed: 0,
    elapsedTimer: null,
    retrying: false,
    error: '',
  }
  taskList.value.unshift(task)
  url.value = ''
  submitting.value = true

  try {
    const { data } = await submitAnalysis(trimmed)
    const realId = data.data.id
    task.id = realId
    task.frontendStatus = 'pending'
    startPolling(task)
    ElMessage.success('任务已提交')
  } catch (err) {
    task.frontendStatus = 'submit_failed'
    task.error = err.response?.data?.message || '提交失败，请检查网络'
  } finally {
    submitting.value = false
  }
}

async function retrySubmit(task) {
  task.frontendStatus = 'submitting'
  try {
    const { data } = await submitAnalysis(task.url)
    task.id = data.data.id
    task.frontendStatus = 'pending'
    startPolling(task)
    ElMessage.success('任务已重新提交')
  } catch (err) {
    task.frontendStatus = 'submit_failed'
    task.error = err.response?.data?.message || '提交失败'
  }
}

// ─── 轮询 ──────────────────────────────────────

function startPolling(task) {
  stopPolling(task)
  task.pollCount = 0
  startElapsed(task)

  task.pollTimer = setInterval(async () => {
    task.pollCount++
    try {
      const { data } = await getAnalysis(task.id)
      const remoteStatus = data.data.status

      if (remoteStatus === 'success') {
        Object.assign(task, data.data, { frontendStatus: 'success' })
        stopPolling(task)
        stopElapsed(task)
        ElMessage.success('分析完成')
      } else if (remoteStatus === 'failed') {
        Object.assign(task, data.data, { frontendStatus: 'failed' })
        stopPolling(task)
        stopElapsed(task)
      } else {
        task.frontendStatus = remoteStatus // pending / running
      }
    } catch (err) {
      if (err.response?.status === 404) {
        task.frontendStatus = 'not_found'
        stopPolling(task)
        stopElapsed(task)
      } else {
        task.frontendStatus = 'query_error'
        // 不停止，继续重试
      }
    }

    // 超时检查
    if (task.pollCount >= MAX_POLLS && !['success', 'failed'].includes(task.frontendStatus)) {
      stopPolling(task)
      stopElapsed(task)
      if (task.frontendStatus !== 'not_found') {
        task.frontendStatus = 'timeout'
      }
    }
  }, 2000)
}

function stopPolling(task) {
  if (task.pollTimer) {
    clearInterval(task.pollTimer)
    task.pollTimer = null
  }
}

function startElapsed(task) {
  task.elapsed = 0
  task.elapsedTimer = setInterval(() => {
    task.elapsed++
  }, 1000)
}

function stopElapsed(task) {
  if (task.elapsedTimer) {
    clearInterval(task.elapsedTimer)
    task.elapsedTimer = null
  }
}

// ─── 重试 ──────────────────────────────────────

async function retryTask(task) {
  task.retrying = true
  try {
    const { data } = await retryAnalysis(task.id)
    task.frontendStatus = 'pending'
    task.pollCount = 0
    task.error_message = ''
    startPolling(task)
    ElMessage.success('任务已重新提交到队列')
  } catch (err) {
    ElMessage.error('重试失败：' + (err.response?.data?.message || '网络异常'))
  } finally {
    task.retrying = false
  }
}

function removeTask(taskId) {
  const idx = taskList.value.findIndex((t) => t.id === taskId)
  if (idx !== -1) {
    stopPolling(taskList.value[idx])
    stopElapsed(taskList.value[idx])
    taskList.value.splice(idx, 1)
  }
}

onUnmounted(() => {
  taskList.value.forEach((t) => {
    stopPolling(t)
    stopElapsed(t)
  })
})
</script>

<style scoped>
.dashboard {
  padding: 40px;
  max-width: 800px;
  margin: 0 auto;
}
h1 {
  margin-bottom: 8px;
}
.subtitle {
  color: #909399;
  font-size: 14px;
  margin-bottom: 30px;
}
.input-row {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}
.url-input {
  flex: 1;
}
.result-card {
  margin-top: 20px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.card-url {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 70%;
  font-size: 13px;
  color: #606266;
}
.result-item {
  margin-bottom: 16px;
}
.summary-text {
  color: #606266;
  line-height: 1.6;
  margin-top: 4px;
}
.keyword-tag {
  margin-right: 6px;
}
.result-meta {
  color: #c0c4cc;
  font-size: 12px;
  margin-top: 16px;
}
.elapsed-time {
  color: #909399;
  font-size: 12px;
  margin-top: 8px;
}
</style>