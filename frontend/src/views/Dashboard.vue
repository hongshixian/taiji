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

    <!-- 错误提示 -->
    <el-alert
      v-if="error"
      :title="error"
      type="error"
      show-icon
      closable
      class="alert"
      @close="error = ''"
    />

    <!-- 当前分析结果 -->
    <div v-if="currentTask" class="result-card">
      <el-card>
        <template #header>
          <div class="card-header">
            <span>分析结果</span>
            <el-tag :type="statusTag" size="small">
              {{ statusLabel }}
            </el-tag>
          </div>
        </template>

        <!-- 加载中 -->
        <el-skeleton v-if="loading" :rows="6" animated />

        <!-- 成功结果 -->
        <template v-else-if="currentTask.status === 'success'">
          <div class="result-item">
            <strong>标题：</strong>{{ currentTask.title }}
          </div>
          <div class="result-item">
            <strong>摘要：</strong>
            <p class="summary-text">{{ currentTask.summary }}</p>
          </div>
          <div v-if="currentTask.keywords?.length" class="result-item">
            <strong>关键词：</strong>
            <el-tag
              v-for="kw in currentTask.keywords"
              :key="kw"
              class="keyword-tag"
              size="small"
            >
              {{ kw }}
            </el-tag>
          </div>
          <div class="result-meta">
            分析完成于 {{ formatTime(currentTask.completed_at) }}
          </div>
        </template>

        <!-- 失败 -->
        <el-alert
          v-else-if="currentTask.status === 'failed'"
          :title="'分析失败'"
          :description="currentTask.error_message"
          type="error"
          show-icon
        />
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { submitAnalysis, getAnalysis } from '../api/analyze'

const url = ref('')
const submitting = ref(false)
const loading = ref(false)
const error = ref('')
const currentTask = ref(null)
let pollTimer = null

const statusLabel = computed(() => {
  const map = { pending: '排队中', running: '分析中', success: '已完成', failed: '失败' }
  return map[currentTask.value?.status] || currentTask.value?.status
})

const statusTag = computed(() => {
  const map = { pending: 'info', running: 'warning', success: 'success', failed: 'danger' }
  return map[currentTask.value?.status] || 'info'
})

async function handleSubmit() {
  const trimmed = url.value.trim()
  if (!trimmed) {
    error.value = '请输入 URL'
    return
  }
  if (!trimmed.startsWith('http://') && !trimmed.startsWith('https://')) {
    error.value = 'URL 必须以 http:// 或 https:// 开头'
    return
  }

  error.value = ''
  submitting.value = true
  try {
    const { data } = await submitAnalysis(trimmed)
    currentTask.value = data.data
    ElMessage.success('任务已提交')
    startPolling(data.data.id)
  } catch (err) {
    error.value = err.response?.data?.message || '提交失败'
  } finally {
    submitting.value = false
  }
}

function startPolling(taskId) {
  stopPolling()
  loading.value = true

  pollTimer = setInterval(async () => {
    try {
      const { data } = await getAnalysis(taskId)
      currentTask.value = data.data

      if (['success', 'failed'].includes(data.data.status)) {
        stopPolling()
        loading.value = false
        ElMessage.success('分析完成')
      }
    } catch {
      stopPolling()
      loading.value = false
      error.value = '查询任务状态失败'
    }
  }, 2000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function formatTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString('zh-CN')
}

onUnmounted(stopPolling)
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
.alert {
  margin-bottom: 16px;
}
.result-card {
  margin-top: 24px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
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
</style>