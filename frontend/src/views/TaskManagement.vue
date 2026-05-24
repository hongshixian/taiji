<template>
  <div class="task-management">
    <div class="top-bar">
      <h2>任务管理</h2>
      <el-button type="primary" @click="showDialog = true">+ 创建任务</el-button>
    </div>

    <!-- 创建任务弹窗 -->
    <el-dialog v-model="showDialog" title="创建分析任务" width="500px" :close-on-click-modal="false">
      <el-form @submit.prevent="handleSubmit">
        <el-form-item label="目标 URL">
          <el-input v-model="url" placeholder="https://example.com" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">提交分析</el-button>
      </template>
    </el-dialog>

    <!-- 任务卡片 -->
    <div v-if="taskList.length === 0 && !submitting" class="empty-state">
      <p>暂无任务，点击上方按钮创建</p>
    </div>

    <div v-for="task in taskList" :key="task.id" class="result-card">
      <el-card>
        <template #header>
          <div class="card-header">
            <span class="card-url">{{ task.url }}</span>
            <el-tag :type="statusTag(task.frontendStatus)" size="small">
              {{ statusLabel(task.frontendStatus) }}
            </el-tag>
          </div>
        </template>

        <el-skeleton v-if="['submitting', 'pending', 'running'].includes(task.frontendStatus)" :rows="4" animated />
        <div v-if="['pending', 'running'].includes(task.frontendStatus)" class="elapsed-time">
          已等待 {{ task.elapsed }} 秒
        </div>

        <template v-else-if="task.frontendStatus === 'success'">
          <div class="result-item"><strong>标题：</strong>{{ task.title }}</div>
          <div class="result-item"><strong>摘要：</strong><p class="summary-text">{{ task.summary }}</p></div>
          <div v-if="task.keywords?.length" class="result-item">
            <strong>关键词：</strong>
            <el-tag v-for="kw in task.keywords" :key="kw" class="keyword-tag" size="small">{{ kw }}</el-tag>
          </div>
          <div class="result-meta">完成于 {{ formatTime(task.completed_at) }}</div>
        </template>

        <el-alert
          v-else-if="task.frontendStatus === 'submit_failed'"
          title="提交失败" :description="task.error" type="error" show-icon :closable="false">
          <template #default>
            <el-button size="small" type="primary" @click="retrySubmit(task)">重新提交</el-button>
            <el-button size="small" @click="removeTask(task.id)">关闭</el-button>
          </template>
        </el-alert>

        <el-alert
          v-else-if="task.frontendStatus === 'failed'"
          title="分析失败" :description="task.error_message" type="error" show-icon :closable="false">
          <template #default>
            <el-button size="small" type="primary" :loading="task.retrying" @click="retryTask(task)">重新分析</el-button>
            <el-button size="small" @click="removeTask(task.id)">关闭</el-button>
          </template>
        </el-alert>

        <el-alert
          v-else-if="task.frontendStatus === 'timeout'"
          title="分析超时" description="超过 60 秒未完成" type="warning" show-icon :closable="false">
          <template #default>
            <el-button size="small" type="primary" :loading="task.retrying" @click="retryTask(task)">重新分析</el-button>
            <el-button size="small" @click="removeTask(task.id)">关闭</el-button>
          </template>
        </el-alert>

        <el-alert
          v-else-if="task.frontendStatus === 'not_found'"
          title="任务丢失" description="Worker 可能异常" type="warning" show-icon :closable="false">
          <template #default>
            <el-button size="small" type="primary" :loading="task.retrying" @click="retryTask(task)">重新分析</el-button>
            <el-button size="small" @click="removeTask(task.id)">关闭</el-button>
          </template>
        </el-alert>

        <el-alert
          v-else-if="task.frontendStatus === 'query_error'"
          title="查询失败" description="正在自动重试..." type="info" show-icon :closable="false">
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

const MAX_POLLS = 30
const showDialog = ref(false)
const url = ref('')
const submitting = ref(false)
const taskList = ref([])

const statusLabel = (s) => {
  const map = { submitting:'提交中', submit_failed:'提交失败', pending:'排队中', running:'分析中', success:'已完成', failed:'失败', timeout:'超时', not_found:'任务丢失', query_error:'查询异常' }
  return map[s] || s
}
const statusTag = (s) => {
  const map = { submitting:'info', submit_failed:'danger', pending:'info', running:'warning', success:'success', failed:'danger', timeout:'warning', not_found:'warning', query_error:'info' }
  return map[s] || 'info'
}
function formatTime(iso) { return iso ? new Date(iso).toLocaleString('zh-CN') : '' }

async function handleSubmit() {
  const trimmed = url.value.trim()
  if (!trimmed) return ElMessage.warning('请输入 URL')
  if (!trimmed.startsWith('http://') && !trimmed.startsWith('https://'))
    return ElMessage.warning('URL 必须以 http:// 或 https:// 开头')

  showDialog.value = false
  url.value = ''
  const taskId = Date.now()
  const task = { id: taskId, url: trimmed, frontendStatus: 'submitting', pollCount: 0, pollTimer: null, elapsed: 0, elapsedTimer: null, retrying: false, error: '' }
  taskList.value.unshift(task)
  submitting.value = true

  try {
    const { data } = await submitAnalysis(trimmed)
    task.id = data.data.id
    task.frontendStatus = 'pending'
    startPolling(task)
    ElMessage.success('任务已提交')
  } catch (err) {
    task.frontendStatus = 'submit_failed'
    task.error = err.response?.data?.message || '提交失败'
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
    ElMessage.success('已重新提交')
  } catch (err) {
    task.frontendStatus = 'submit_failed'
    task.error = err.response?.data?.message || '提交失败'
  }
}

function startPolling(task) {
  stopPolling(task)
  task.pollCount = 0
  task.elapsedTimer = setInterval(() => task.elapsed++, 1000)

  task.pollTimer = setInterval(async () => {
    task.pollCount++
    try {
      const { data } = await getAnalysis(task.id)
      const s = data.data.status
      if (s === 'success' || s === 'failed') {
        Object.assign(task, data.data, { frontendStatus: s })
        stopPolling(task)
        if (s === 'success') ElMessage.success('分析完成')
      } else {
        task.frontendStatus = s
      }
    } catch (err) {
      if (err.response?.status === 404) { task.frontendStatus = 'not_found'; stopPolling(task) }
      else task.frontendStatus = 'query_error'
    }
    if (task.pollCount >= MAX_POLLS && !['success','failed'].includes(task.frontendStatus)) {
      stopPolling(task)
      if (task.frontendStatus !== 'not_found') task.frontendStatus = 'timeout'
    }
  }, 2000)
}

function stopPolling(task) {
  clearInterval(task.pollTimer)
  clearInterval(task.elapsedTimer)
  task.pollTimer = null
  task.elapsedTimer = null
}

async function retryTask(task) {
  task.retrying = true
  try {
    const { data } = await retryAnalysis(task.id)
    task.frontendStatus = 'pending'
    task.pollCount = 0
    task.error_message = ''
    startPolling(task)
    ElMessage.success('已重新提交到队列')
  } catch (err) {
    ElMessage.error('重试失败：' + (err.response?.data?.message || '网络异常'))
  } finally { task.retrying = false }
}

function removeTask(taskId) {
  const idx = taskList.value.findIndex(t => t.id === taskId)
  if (idx !== -1) { stopPolling(taskList.value[idx]); taskList.value.splice(idx, 1) }
}

onUnmounted(() => taskList.value.forEach(stopPolling))
</script>

<style scoped>
.task-management { max-width: 900px; }
.top-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.empty-state { text-align: center; color: #909399; padding: 60px 0; }
.result-card { margin-bottom: 16px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.card-url { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 70%; font-size: 13px; color: #606266; }
.result-item { margin-bottom: 12px; }
.summary-text { color: #606266; line-height: 1.6; margin-top: 4px; }
.keyword-tag { margin-right: 4px; }
.result-meta { color: #c0c4cc; font-size: 12px; margin-top: 12px; }
.elapsed-time { color: #909399; font-size: 12px; margin-top: 8px; }
</style>
