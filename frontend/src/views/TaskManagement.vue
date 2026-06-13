<template>
  <div class="page-shell webpage-task">
    <header class="page-header">
      <span class="page-header__eyebrow t-eyebrow">任务 · 网页内容分析</span>
      <div class="page-header__row">
        <h1 class="page-header__title">网页内容分析</h1>
        <el-button type="primary" @click="showDialog = true">
          <el-icon><Plus /></el-icon>&nbsp;新建任务
        </el-button>
      </div>
      <p class="page-header__lede">
        提交一个公网 URL，由 Worker 异步抓取并提取标题与正文。任务在当前租户内可见。
      </p>
    </header>

    <!-- 概览指标 -->
    <section class="metric-strip">
      <div class="metric">
        <span class="t-eyebrow">进行中</span>
        <span class="t-mono metric-value">{{ activeTasks.length }}</span>
      </div>
      <div class="metric">
        <span class="t-eyebrow">历史记录</span>
        <span class="t-mono metric-value">{{ total }}</span>
      </div>
      <div class="metric">
        <span class="t-eyebrow">轮询超时</span>
        <span class="t-mono metric-value">{{ MAX_POLLS * 2 }} 秒</span>
      </div>
    </section>

    <!-- 创建任务弹窗 -->
    <el-dialog v-model="showDialog" title="新建分析任务" width="500px" :close-on-click-modal="false">
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
    <section v-if="activeTasks.length" class="task-section">
      <div class="task-section__header">
        <span class="t-eyebrow">进行中</span>
        <span class="t-caption">{{ activeTasks.length }} 个任务正在轮询</span>
      </div>
      <div class="active-list">
        <article v-for="task in activeTasks" :key="'a-' + task.id" class="active-card">
          <header class="active-card__header">
            <span class="active-card__url" :title="task.url">{{ task.url }}</span>
            <div class="active-card__actions">
              <span class="status-pill" :data-tone="statusTone(task.frontendStatus)">
                {{ statusLabel(task.frontendStatus) }}
              </span>
              <el-button v-if="canOpenTaskLogs(task)" text type="primary" size="small" @click="openTaskLogs(task)">日志</el-button>
            </div>
          </header>
          <el-skeleton :rows="2" animated />
          <footer class="active-card__meta">
            <span class="t-caption">已等待</span>
            <span class="t-mono">{{ task.elapsed }}s</span>
            <span class="t-caption">·</span>
            <span class="t-caption">轮询</span>
            <span class="t-mono">{{ task.pollCount }}/{{ MAX_POLLS }}</span>
          </footer>
        </article>
      </div>
    </section>

    <!-- 历史任务表格 -->
    <section v-if="historyTasks.length" class="task-section" data-density="compact">
      <div class="task-section__header">
        <span class="t-eyebrow">历史记录</span>
        <span class="t-caption">第 {{ page }} 页 · 每页 {{ perPage }} 条</span>
      </div>
      <el-table :data="historyTasks" stripe v-loading="tableLoading" class="history-table">
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
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <span class="status-pill" :data-tone="dbStatusTone(row.status)">
              {{ dbStatusLabel(row.status) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="日志" width="80">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="openTaskLogs(row)">日志</el-button>
          </template>
        </el-table-column>
        <el-table-column label="提交时间" width="170">
          <template #default="{ row }">
            <span class="t-mono">{{ formatTime(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button v-if="row.status === 'failed'" text type="primary" size="small" @click="retryDbTask(row)">重新分析</el-button>
            <el-button v-if="has('task:delete:any')" text type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-if="total > perPage"
        v-model:current-page="page"
        :page-size="perPage"
        :total="total"
        layout="prev, pager, next"
        class="pagination"
        @current-change="fetchHistoryTasks"
      />
    </section>

    <!-- 空状态 -->
    <section v-if="activeTasks.length === 0 && historyTasks.length === 0 && !tableLoading" class="empty-state">
      <span class="t-eyebrow">暂无任务</span>
      <h3 class="empty-state__title">还没有提交过分析任务</h3>
      <p class="empty-state__lede">输入一个公网 URL 开始抓取。Worker 会在后台异步处理。</p>
      <el-button type="primary" @click="showDialog = true">
        <el-icon><Plus /></el-icon>&nbsp;提交第一个任务
      </el-button>
    </section>

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
const activeTasks = ref([])
const historyTasks = ref([])
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
// tone:neutral / progress / success / warning / danger
const statusTone = (s) => {
  const map = { submitting:'progress', submit_failed:'danger', pending:'neutral', running:'progress', success:'success', failed:'danger', timeout:'warning', not_found:'warning', query_error:'neutral' }
  return map[s] || 'neutral'
}
const dbStatusLabel = (s) => {
  const map = { pending:'排队中', running:'分析中', success:'已完成', failed:'失败' }
  return map[s] || s
}
const dbStatusTone = (s) => {
  const map = { pending:'neutral', running:'progress', success:'success', failed:'danger' }
  return map[s] || 'neutral'
}
function formatTime(iso) { return iso ? new Date(iso).toLocaleString('zh-CN') : '' }

function openTaskLogs(row) { taskLogDialogRef.value?.open(row) }
function canOpenTaskLogs(task) { return !['submitting', 'submit_failed'].includes(task.frontendStatus) }

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
    await ElMessageBox.confirm('确定删除该任务？删除后不可恢复。', '删除确认', {
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
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
.webpage-task {
  display: flex;
  flex-direction: column;
  gap: var(--space-9);
}

.page-header__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-7);
}

/* ─── 指标条 ─── */
.metric-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--space-7);
  padding: var(--space-7) var(--space-8);
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xs);
}
.metric { display: flex; flex-direction: column; gap: var(--space-3); }
.metric-value {
  font-size: var(--text-3xl);
  color: var(--fg-primary);
  font-weight: var(--weight-semibold);
}

/* ─── 任务区块 ─── */
.task-section { display: flex; flex-direction: column; gap: var(--space-6); }
.task-section__header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}

/* ─── 进行中卡片 ─── */
.active-list { display: flex; flex-direction: column; gap: var(--space-5); }
.active-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: var(--space-7) var(--space-8);
  box-shadow: var(--shadow-xs);
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  transition: box-shadow var(--dur-base) var(--ease-out),
              border-color var(--dur-base) var(--ease-out);
}
.active-card:hover {
  box-shadow: var(--shadow-sm);
  border-color: var(--border-default);
}
.active-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-5);
}
.active-card__url {
  flex: 1;
  min-width: 0;
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--fg-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.active-card__actions {
  display: flex;
  align-items: center;
  gap: var(--space-5);
  flex-shrink: 0;
}
.active-card__meta {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
  color: var(--fg-secondary);
}

/* ─── 状态徽章（自定义，不用 el-tag 以脱离 primary 色映射）─── */
.status-pill {
  display: inline-flex;
  align-items: center;
  padding: 2px var(--space-5);
  border-radius: var(--radius-full);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  letter-spacing: 0.02em;
  background: var(--badge-bg-neutral);
  color: var(--badge-fg-neutral);
  border: 1px solid transparent;
  white-space: nowrap;
}
.status-pill[data-tone='success'] {
  background: var(--color-success-bg);
  color: var(--color-success-fg);
  border-color: var(--color-success-border);
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
.status-pill[data-tone='progress'] {
  background: var(--color-info-bg);
  color: var(--color-info-fg);
  border-color: var(--color-info-border);
}

/* ─── 历史表格 ─── */
.history-table {
  width: 100%;
  border-radius: var(--radius-lg);
  overflow: hidden;
  border: 1px solid var(--border-subtle);
}
.url-text {
  color: var(--violet-600);
  cursor: pointer;
  word-break: break-all;
  font-family: var(--font-mono);
  font-size: var(--text-sm);
}
.url-text:hover { color: var(--violet-700); text-decoration: underline; }
[data-theme="dark"] .url-text,
html.dark .url-text { color: var(--violet-300); }
[data-theme="dark"] .url-text:hover,
html.dark .url-text:hover { color: var(--violet-200); }

.pagination { margin-top: var(--space-6); justify-content: center; }

/* ─── 空状态 ─── */
.empty-state {
  background: var(--bg-surface);
  border: 1px dashed var(--border-default);
  border-radius: var(--radius-lg);
  padding: var(--space-12) var(--space-9);
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-5);
}
.empty-state__title {
  margin: 0;
  font-size: var(--text-2xl);
  color: var(--fg-primary);
}
.empty-state__lede {
  margin: 0;
  color: var(--fg-secondary);
  max-width: 48ch;
}
.empty-state .el-button { margin-top: var(--space-3); }

@media (max-width: 768px) {
  .page-header__row { flex-direction: column; align-items: flex-start; }
}
</style>
