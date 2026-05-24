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

    <!-- 进行中任务卡片 -->
    <h3 v-if="activeTasks.length" class="section-title">进行中</h3>
    <div v-for="task in activeTasks" :key="'a-' + task.id" class="result-card">
      <el-card>
        <template #header>
          <div class="card-header">
            <span class="card-url">{{ task.url }}</span>
            <el-tag :type="statusTag(task.frontendStatus)" size="small">
              {{ statusLabel(task.frontendStatus) }}
            </el-tag>
          </div>
        </template>
        <el-skeleton :rows="3" animated />
        <div class="elapsed-time">已等待 {{ task.elapsed }} 秒</div>
      </el-card>
    </div>

    <!-- 历史任务表格 -->
    <h3 v-if="historyTasks.length" class="section-title">历史记录</h3>
    <el-table v-if="historyTasks.length" :data="historyTasks" stripe v-loading="tableLoading" class="history-table">
      <el-table-column label="URL" min-width="280">
        <template #default="{ row }">
          <span class="url-text">{{ row.url }}</span>
        </template>
      </el-table-column>
      <el-table-column label="标题" min-width="180">
        <template #default="{ row }">{{ row.title || '—' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="dbStatusTag(row.status)" size="small">{{ dbStatusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="提交时间" width="170">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button v-if="row.status === 'failed'" text type="primary" size="small" @click="retryDbTask(row)">重新分析</el-button>
          <span v-else style="color:#c0c4cc">—</span>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <el-pagination
      v-if="total > perPage"
      v-model:current-page="page"
      :page-size="perPage"
      :total="total"
      layout="prev, pager, next"
      class="pagination"
      @current-change="fetchHistoryTasks"
    />

    <!-- 空状态 -->
    <div v-if="activeTasks.length === 0 && historyTasks.length === 0 && !tableLoading" class="empty-state">
      <el-empty description="暂无任务，点击上方按钮创建" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { submitAnalysis, getAnalysis, retryAnalysis, listAnalyses } from '../api/analyze'

const MAX_POLLS = 30
const showDialog = ref(false)
const url = ref('')
const submitting = ref(false)
const activeTasks = ref([])      // 进行中的（前端追踪）
const historyTasks = ref([])      // 历史任务（后端加载）
const tableLoading = ref(false)
const page = ref(1)
const perPage = 20
const total = ref(0)

const statusLabel = (s) => {
  const map = { submitting:'提交中', submit_failed:'提交失败', pending:'排队中', running:'分析中', success:'已完成', failed:'失败', timeout:'超时', not_found:'任务丢失', query_error:'查询异常' }
  return map[s] || s
}
const statusTag = (s) => {
  const map = { submitting:'info', submit_failed:'danger', pending:'info', running:'warning', success:'success', failed:'danger', timeout:'warning', not_found:'warning', query_error:'info' }
  return map[s] || 'info'
}
const dbStatusLabel = (s) => {
  const map = { pending:'排队中', running:'分析中', success:'已完成', failed:'失败' }
  return map[s] || s
}
const dbStatusTag = (s) => {
  const map = { pending:'info', running:'warning', success:'success', failed:'danger' }
  return map[s] || 'info'
}
function formatTime(iso) { return iso ? new Date(iso).toLocaleString('zh-CN') : '' }

// ─── 历史任务 ─────────────────────────────

async function fetchHistoryTasks() {
  tableLoading.value = true
  try {
    const { data } = await listAnalyses(page.value, perPage)
    historyTasks.value = data.data.items
    total.value = data.data.total
  } catch {
    // ignore
  } finally {
    tableLoading.value = false
  }
}

async function retryDbTask(row) {
  try {
    const { data } = await retryAnalysis(row.id)
    // 从历史列表移除，加入进行中
    historyTasks.value = historyTasks.value.filter(t => t.id !== row.id)
    total.value--
    const task = { ...data.data, frontendStatus: 'pending', pollCount: 0, pollTimer: null, elapsed: 0, elapsedTimer: null, retrying: false }
    activeTasks.value.unshift(task)
    startPolling(task)
    ElMessage.success('已重新提交')
  } catch (err) {
    ElMessage.error('重试失败：' + (err.response?.data?.message || '网络异常'))
  }
}

// ─── 创建任务 ─────────────────────────────

async function handleSubmit() {
  const trimmed = url.value.trim()
  if (!trimmed) return ElMessage.warning('请输入 URL')
  if (!trimmed.startsWith('http://') && !trimmed.startsWith('https://'))
    return ElMessage.warning('URL 必须以 http:// 或 https:// 开头')

  showDialog.value = false
  url.value = ''
  const taskId = Date.now()
  const task = { id: taskId, url: trimmed, frontendStatus: 'submitting', pollCount: 0, pollTimer: null, elapsed: 0, elapsedTimer: null, retrying: false, error: '' }
  activeTasks.value.unshift(task)
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
        stopPolling(task)
        // 移到历史列表
        activeTasks.value = activeTasks.value.filter(t => t.id !== task.id)
        historyTasks.value.unshift(data.data)
        total.value++
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

onMounted(fetchHistoryTasks)
onUnmounted(() => activeTasks.value.forEach(stopPolling))
</script>

<style scoped>
.task-management { max-width: 1000px; }
.top-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.section-title { margin-bottom: 12px; color: #303133; font-size: 15px; }
.result-card { margin-bottom: 12px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.card-url { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 70%; font-size: 13px; color: #606266; }
.elapsed-time { color: #909399; font-size: 12px; margin-top: 8px; }
.history-table { width: 100%; }
.url-text { color: #409eff; cursor: pointer; word-break: break-all; }
.pagination { margin-top: 16px; justify-content: center; }
.empty-state { padding: 40px 0; }
</style>
