<template>
  <div class="task-management">
    <div class="top-bar">
      <div class="page-title">
        <el-icon class="page-icon"><Tickets /></el-icon>
        <h2>网页内容分析</h2>
      </div>
      <el-button type="primary" size="default" @click="showDialog = true">
        <el-icon><Plus /></el-icon>&nbsp;创建任务
      </el-button>
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
            <div class="card-actions">
              <el-tag :type="statusTag(task.frontendStatus)" size="small">
                {{ statusLabel(task.frontendStatus) }}
              </el-tag>
              <el-button v-if="canOpenTaskLogs(task)" text type="primary" size="small" @click="openTaskLogs(task)">日志</el-button>
            </div>
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
      <el-table-column label="创建者" width="120">
        <template #default="{ row }">{{ row.username || '—' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="dbStatusTag(row.status)" size="small">{{ dbStatusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="日志" width="80">
        <template #default="{ row }">
          <el-button text type="primary" size="small" @click="openTaskLogs(row)">日志</el-button>
        </template>
      </el-table-column>
      <el-table-column label="提交时间" width="170">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="160">
        <template #default="{ row }">
          <el-button v-if="row.status === 'failed'" text type="primary" size="small" @click="retryDbTask(row)">重新分析</el-button>
          <el-button v-if="has('task:delete:any')" text type="danger" size="small" @click="handleDelete(row)">删除</el-button>
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

    <TaskLogDialog ref="taskLogDialogRef" />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  deleteWebpageAnalysis,
  getWebpageAnalysis,
  listWebpageAnalyses,
  retryWebpageAnalysis,
  submitWebpageAnalysis,
} from '../api/webpageAnalysis'
import TaskLogDialog from '../components/TaskLogDialog.vue'
import { usePermission } from '../composables/usePermission'

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
const { has } = usePermission()
const taskLogDialogRef = ref(null)

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

function openTaskLogs(row) {
  taskLogDialogRef.value?.open(row)
}

function canOpenTaskLogs(task) {
  return !['submitting', 'submit_failed'].includes(task.frontendStatus)
}

// ─── 历史任务 ─────────────────────────────

async function fetchHistoryTasks() {
  tableLoading.value = true
  try {
    const { data } = await listWebpageAnalyses(page.value, perPage)
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
    const { data } = await retryWebpageAnalysis(row.id)
    // 从历史列表移除，加入进行中
    historyTasks.value = historyTasks.value.filter(t => t.id !== row.id)
    total.value--
    const newId = data.data.id
    activeTasks.value.unshift({ ...data.data, id: newId, frontendStatus: 'pending', pollCount: 0, pollTimer: null, elapsed: 0, elapsedTimer: null, retrying: false })
    startPolling(newId)
    ElMessage.success('已重新提交')
  } catch (err) {
    ElMessage.error('重试失败：' + (err.response?.data?.message || '网络异常'))
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm('确定要删除该任务吗？删除后不可恢复。', '删除确认', {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return // 取消
  }
  try {
    await deleteWebpageAnalysis(row.id)
    historyTasks.value = historyTasks.value.filter(t => t.id !== row.id)
    total.value--
    ElMessage.success('任务已删除')
  } catch (err) {
    ElMessage.error('删除失败：' + (err.response?.data?.message || '网络异常'))
  }
}

// ─── 创建任务 ─────────────────────────────

/** 通过 reactive proxy 更新 activeTasks 中的任务属性，确保 Vue 响应式追踪 */
function _updateActiveTask(taskId, updates) {
  const idx = activeTasks.value.findIndex(t => t.id === taskId)
  if (idx !== -1) Object.assign(activeTasks.value[idx], updates)
}

function _getActiveTask(taskId) {
  return activeTasks.value.find(t => t.id === taskId)
}

async function handleSubmit() {
  const trimmed = url.value.trim()
  if (!trimmed) return ElMessage.warning('请输入 URL')
  if (!trimmed.startsWith('http://') && !trimmed.startsWith('https://'))
    return ElMessage.warning('URL 必须以 http:// 或 https:// 开头')

  showDialog.value = false
  url.value = ''
  const taskId = Date.now()
  activeTasks.value.unshift({ id: taskId, url: trimmed, frontendStatus: 'submitting', pollCount: 0, pollTimer: null, elapsed: 0, elapsedTimer: null, retrying: false, error: '' })
  submitting.value = true

  try {
    const { data } = await submitWebpageAnalysis(trimmed)
    _updateActiveTask(taskId, { id: data.data.id, frontendStatus: 'pending' })
    startPolling(data.data.id)
    ElMessage.success('任务已提交')
  } catch (err) {
    _updateActiveTask(taskId, { frontendStatus: 'submit_failed', error: err.response?.data?.message || '提交失败' })
  } finally {
    submitting.value = false
  }
}

function startPolling(taskId) {
  stopPolling(taskId)
  _updateActiveTask(taskId, { pollCount: 0 })
  const task = _getActiveTask(taskId)
  if (!task) return

  task.elapsedTimer = setInterval(() => {
    const t = _getActiveTask(taskId)
    if (t) t.elapsed++
  }, 1000)

  task.pollTimer = setInterval(async () => {
    const t = _getActiveTask(taskId)
    if (!t) { stopPolling(taskId); return }
    _updateActiveTask(taskId, { pollCount: t.pollCount + 1 })
    try {
      const { data } = await getWebpageAnalysis(t.id)
      const s = data.data.status
      if (s === 'success' || s === 'failed') {
        stopPolling(taskId)
        // 移到历史列表
        activeTasks.value = activeTasks.value.filter(x => x.id !== taskId)
        historyTasks.value.unshift(data.data)
        total.value++
        if (s === 'success') ElMessage.success('分析完成')
      } else {
        _updateActiveTask(taskId, { frontendStatus: s })
      }
    } catch (err) {
      if (err.response?.status === 404) { _updateActiveTask(taskId, { frontendStatus: 'not_found' }); stopPolling(taskId) }
      else _updateActiveTask(taskId, { frontendStatus: 'query_error' })
    }
    const current = _getActiveTask(taskId)
    if (current && current.pollCount >= MAX_POLLS && !['success','failed'].includes(current.frontendStatus)) {
      stopPolling(taskId)
      if (current.frontendStatus !== 'not_found') _updateActiveTask(taskId, { frontendStatus: 'timeout' })
    }
  }, 2000)
}

function stopPolling(taskId) {
  const t = _getActiveTask(taskId)
  if (t) {
    clearInterval(t.pollTimer)
    clearInterval(t.elapsedTimer)
    t.pollTimer = null
    t.elapsedTimer = null
  }
}

onMounted(fetchHistoryTasks)
onUnmounted(() => activeTasks.value.forEach(t => {
  clearInterval(t.pollTimer)
  clearInterval(t.elapsedTimer)
}))
</script>

<style scoped>
.task-management { max-width: 1200px; margin: 0 auto; }
.top-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.page-title { display: flex; align-items: center; gap: 10px; }
.page-title h2 { margin: 0; font-weight: 600; color: var(--el-text-color-primary); }
.page-icon { font-size: 22px; color: var(--taiji-accent); }
.section-title { margin: 0 0 12px; color: var(--el-text-color-regular); font-size: 14px; font-weight: 500; letter-spacing: 1px; }
.result-card { margin-bottom: 12px; }
.card-header { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.card-actions { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.card-url { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 70%; font-size: 13px; color: var(--el-text-color-regular); }
.elapsed-time { color: var(--el-text-color-secondary); font-size: 12px; margin-top: 8px; }
.history-table { width: 100%; border-radius: var(--taiji-radius-sm); overflow: hidden; }
.url-text { color: var(--el-color-primary); cursor: pointer; word-break: break-all; }
.url-text:hover { color: var(--taiji-accent); text-decoration: underline; }
.pagination { margin-top: 16px; justify-content: center; }
.empty-state { padding: 60px 0; }
</style>
