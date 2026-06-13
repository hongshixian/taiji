<template>
  <div class="page-shell csv-task">
    <header class="page-header">
      <span class="page-header__eyebrow t-eyebrow">任务 · CSV 数据检查</span>
      <div class="page-header__row">
        <h1 class="page-header__title">CSV 数据质量检查</h1>
        <el-button type="primary" @click="showDialog = true">
          <el-icon><Plus /></el-icon>&nbsp;新建任务
        </el-button>
      </div>
      <p class="page-header__lede">
        上传 CSV，由 Worker 推断字段类型并检测空值、重复行与异常。任务在当前租户内可见。
      </p>
    </header>

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

    <el-dialog v-model="showDialog" title="新建 CSV 检查任务" width="680px" :close-on-click-modal="false">
      <el-form label-position="top" @submit.prevent="handleSubmit">
        <el-form-item label="任务名">
          <el-input v-model="taskName" placeholder="例如:6 月用户导入数据检查" maxlength="100" show-word-limit />
        </el-form-item>
        <el-form-item label="CSV 文件">
          <el-upload
            class="csv-upload"
            drag
            action="#"
            accept=".csv,text/csv"
            :auto-upload="false"
            :limit="1"
            :file-list="fileList"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
            :on-exceed="handleFileExceed"
          >
            <el-icon class="upload-icon"><UploadFilled /></el-icon>
            <div class="el-upload__text">拖拽 CSV 文件到此处，或点击选择</div>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">提交检查</el-button>
      </template>
    </el-dialog>

    <section v-if="activeTasks.length" class="task-section">
      <div class="task-section__header">
        <span class="t-eyebrow">进行中</span>
        <span class="t-caption">{{ activeTasks.length }} 个任务正在轮询</span>
      </div>
      <div class="active-list">
        <article v-for="task in activeTasks" :key="'a-' + task.id" class="active-card">
          <header class="active-card__header">
            <span class="active-card__title">{{ task.task_name || task.filename || '未命名任务' }}</span>
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

    <section v-if="historyTasks.length" class="task-section" data-density="compact">
      <div class="task-section__header">
        <span class="t-eyebrow">历史记录</span>
        <span class="t-caption">第 {{ page }} 页 · 每页 {{ perPage }} 条</span>
      </div>
      <el-table :data="historyTasks" stripe v-loading="tableLoading" class="history-table">
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="result-detail" v-if="row.result">
              <div class="summary-grid">
                <div class="summary-cell">
                  <span class="t-eyebrow">数据行</span>
                  <strong class="t-mono summary-value">{{ row.result.data_row_count }}</strong>
                </div>
                <div class="summary-cell">
                  <span class="t-eyebrow">字段数</span>
                  <strong class="t-mono summary-value">{{ row.result.column_count }}</strong>
                </div>
                <div class="summary-cell">
                  <span class="t-eyebrow">重复行</span>
                  <strong class="t-mono summary-value">{{ row.result.duplicate_rows }}</strong>
                </div>
              </div>

              <el-alert
                v-if="row.result.warnings?.length"
                type="warning"
                :closable="false"
                class="warning-alert"
              >
                <template #title>{{ row.result.warnings.join('；') }}</template>
              </el-alert>

              <div class="field-section">
                <span class="t-eyebrow detail-title">字段概览</span>
                <el-table :data="fieldRows(row.result)" size="small" border>
                  <el-table-column prop="name" label="字段" min-width="160" />
                  <el-table-column prop="type" label="推断类型" width="120" />
                  <el-table-column prop="empty" label="空值数" width="100" />
                </el-table>
              </div>

              <div class="field-section" v-if="row.result.preview?.length">
                <span class="t-eyebrow detail-title">数据预览</span>
                <el-table :data="row.result.preview" size="small" border>
                  <el-table-column
                    v-for="column in row.result.columns"
                    :key="column"
                    :prop="column"
                    :label="column"
                    min-width="140"
                    show-overflow-tooltip
                  />
                </el-table>
              </div>
            </div>
            <el-empty v-else description="暂无检查结果" :image-size="70" />
          </template>
        </el-table-column>
        <el-table-column label="任务名" min-width="180">
          <template #default="{ row }">{{ row.task_name || '未命名任务' }}</template>
        </el-table-column>
        <el-table-column label="文件名" min-width="180">
          <template #default="{ row }">
            <span class="t-mono">{{ row.filename || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="规模" width="160">
          <template #default="{ row }">
            <span v-if="row.result" class="t-mono">{{ row.result.data_row_count }} 行 · {{ row.result.column_count }} 列</span>
            <span v-else>—</span>
          </template>
        </el-table-column>
        <el-table-column label="风险提示" min-width="160">
          <template #default="{ row }">
            <span v-if="row.result?.warnings?.length" class="status-pill" data-tone="warning">
              {{ row.result.warnings.length }} 项
            </span>
            <span v-else class="t-caption">—</span>
          </template>
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
            <el-button v-if="row.status === 'failed'" text type="primary" size="small" @click="retryDbTask(row)">重新检查</el-button>
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

    <section v-if="activeTasks.length === 0 && historyTasks.length === 0 && !tableLoading" class="empty-state">
      <span class="t-eyebrow">暂无任务</span>
      <h3 class="empty-state__title">还没有上传过 CSV</h3>
      <p class="empty-state__lede">选择一份本地 CSV 文件开始检查。Worker 会在后台处理。</p>
      <el-button type="primary" @click="showDialog = true">
        <el-icon><Plus /></el-icon>&nbsp;上传第一份 CSV
      </el-button>
    </section>

    <TaskLogDialog ref="taskLogDialogRef" />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  deleteCsvQuality,
  getCsvQuality,
  listCsvQuality,
  retryCsvQuality,
  submitCsvQuality,
} from '../api/csvQuality'
import TaskLogDialog from '../components/TaskLogDialog.vue'
import { usePermission } from '../composables/usePermission'

const MAX_POLLS = 30
const showDialog = ref(false)
const taskName = ref('')
const selectedFile = ref(null)
const fileList = ref([])
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
  const map = { submitting:'提交中', submit_failed:'提交失败', pending:'排队中', running:'检查中', success:'已完成', failed:'失败', timeout:'超时', not_found:'任务丢失', query_error:'查询异常' }
  return map[s] || s
}
const statusTone = (s) => {
  const map = { submitting:'progress', submit_failed:'danger', pending:'neutral', running:'progress', success:'success', failed:'danger', timeout:'warning', not_found:'warning', query_error:'neutral' }
  return map[s] || 'neutral'
}
const dbStatusLabel = (s) => {
  const map = { pending:'排队中', running:'检查中', success:'已完成', failed:'失败' }
  return map[s] || s
}
const dbStatusTone = (s) => {
  const map = { pending:'neutral', running:'progress', success:'success', failed:'danger' }
  return map[s] || 'neutral'
}
function formatTime(iso) { return iso ? new Date(iso).toLocaleString('zh-CN') : '' }

function openTaskLogs(row) { taskLogDialogRef.value?.open(row) }
function canOpenTaskLogs(task) { return !['submitting', 'submit_failed'].includes(task.frontendStatus) }

function fieldRows(result) {
  return (result.columns || []).map((name) => ({
    name,
    type: result.type_inference?.[name] || '—',
    empty: result.empty_counts?.[name] ?? 0,
  }))
}

async function fetchHistoryTasks() {
  tableLoading.value = true
  try {
    const { data } = await listCsvQuality(page.value, perPage)
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
    const { data } = await retryCsvQuality(row.id)
    historyTasks.value = historyTasks.value.filter(t => t.id !== row.id)
    total.value--
    const newId = data.data.id
    activeTasks.value.unshift({ ...data.data, id: newId, frontendStatus: 'pending', pollCount: 0, pollTimer: null, elapsed: 0, elapsedTimer: null })
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
    await deleteCsvQuality(row.id)
    historyTasks.value = historyTasks.value.filter(t => t.id !== row.id)
    total.value--
    ElMessage.success('任务已删除')
  } catch (err) {
    ElMessage.error('删除失败：' + (err.response?.data?.message || '网络异常'))
  }
}

function handleFileChange(uploadFile, uploadFiles) {
  const file = uploadFile.raw
  if (!file) return
  if (!file.name.toLowerCase().endsWith('.csv')) {
    fileList.value = []
    selectedFile.value = null
    ElMessage.warning('请选择 .csv 文件')
    return
  }
  selectedFile.value = file
  fileList.value = uploadFiles.slice(-1)
}

function handleFileRemove() {
  selectedFile.value = null
  fileList.value = []
}

function handleFileExceed(files) {
  const file = files[0]
  if (!file) return
  if (!file.name.toLowerCase().endsWith('.csv')) {
    ElMessage.warning('请选择 .csv 文件')
    return
  }
  selectedFile.value = file
  fileList.value = [{ name: file.name, raw: file }]
}

function _updateActiveTask(taskId, updates) {
  const idx = activeTasks.value.findIndex(t => t.id === taskId)
  if (idx !== -1) Object.assign(activeTasks.value[idx], updates)
}
function _getActiveTask(taskId) {
  return activeTasks.value.find(t => t.id === taskId)
}

async function handleSubmit() {
  const name = taskName.value.trim()
  if (!name) return ElMessage.warning('请输入任务名')
  if (!selectedFile.value) return ElMessage.warning('请选择 CSV 文件')

  showDialog.value = false
  const submittedName = name
  const submittedFilename = selectedFile.value.name
  const submittedFile = selectedFile.value
  taskName.value = ''
  selectedFile.value = null
  fileList.value = []
  const taskId = Date.now()
  activeTasks.value.unshift({ id: taskId, task_name: submittedName, filename: submittedFilename, frontendStatus: 'submitting', pollCount: 0, pollTimer: null, elapsed: 0, elapsedTimer: null, error: '' })
  submitting.value = true

  try {
    const { data } = await submitCsvQuality(submittedName, submittedFile)
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
      const { data } = await getCsvQuality(t.id)
      const s = data.data.status
      if (s === 'success' || s === 'failed') {
        stopPolling(taskId)
        activeTasks.value = activeTasks.value.filter(x => x.id !== taskId)
        historyTasks.value.unshift(data.data)
        total.value++
        if (s === 'success') ElMessage.success('检查完成')
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
.csv-task {
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

.task-section { display: flex; flex-direction: column; gap: var(--space-6); }
.task-section__header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}

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
.active-card__title {
  flex: 1;
  min-width: 0;
  font-size: var(--text-md);
  font-weight: var(--weight-semibold);
  color: var(--fg-primary);
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

/* status pill — shared tone system */
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

/* table */
.history-table {
  width: 100%;
  border-radius: var(--radius-lg);
  overflow: hidden;
  border: 1px solid var(--border-subtle);
}

/* expanded result */
.result-detail {
  padding: var(--space-5) var(--space-7) var(--space-7);
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}
.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(120px, 1fr));
  gap: var(--space-5);
}
.summary-cell {
  background: var(--bg-surface-sunken);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: var(--space-6) var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.summary-value {
  font-size: var(--text-2xl);
  font-weight: var(--weight-semibold);
  color: var(--fg-primary);
}
.warning-alert {
  border-radius: var(--radius-md);
}
.field-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.detail-title {
  display: block;
  letter-spacing: 0.18em;
}

.csv-upload { width: 100%; }
.upload-icon {
  font-size: 32px;
  color: var(--fg-tertiary);
  margin-bottom: var(--space-3);
}
.pagination { margin-top: var(--space-6); justify-content: center; }

/* empty state */
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

@media (max-width: 768px) {
  .page-header__row { flex-direction: column; align-items: flex-start; }
  .summary-grid { grid-template-columns: 1fr; }
}
</style>
