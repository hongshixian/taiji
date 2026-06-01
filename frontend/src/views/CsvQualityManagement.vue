<template>
  <div class="csv-quality-management">
    <div class="top-bar">
      <div class="page-title">
        <el-icon class="page-icon"><Grid /></el-icon>
        <h2>CSV 数据质量检查</h2>
      </div>
      <el-button type="primary" size="default" @click="showDialog = true">
        <el-icon><Plus /></el-icon>&nbsp;创建任务
      </el-button>
    </div>

    <el-dialog v-model="showDialog" title="创建 CSV 检查任务" width="680px" :close-on-click-modal="false">
      <el-form label-position="top" @submit.prevent="handleSubmit">
        <el-form-item label="任务名">
          <el-input v-model="taskName" placeholder="例如：6 月用户导入数据检查" maxlength="100" show-word-limit />
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

    <h3 v-if="activeTasks.length" class="section-title">进行中</h3>
    <div v-for="task in activeTasks" :key="'a-' + task.id" class="result-card">
      <el-card>
        <template #header>
          <div class="card-header">
            <span class="card-title-text">{{ task.task_name || task.filename || '未命名任务' }}</span>
            <el-tag :type="statusTag(task.frontendStatus)" size="small">
              {{ statusLabel(task.frontendStatus) }}
            </el-tag>
          </div>
        </template>
        <el-skeleton :rows="3" animated />
        <div class="elapsed-time">已等待 {{ task.elapsed }} 秒</div>
      </el-card>
    </div>

    <h3 v-if="historyTasks.length" class="section-title">历史记录</h3>
    <el-table v-if="historyTasks.length" :data="historyTasks" stripe v-loading="tableLoading" class="history-table">
      <el-table-column type="expand">
        <template #default="{ row }">
          <div class="result-detail" v-if="row.result">
            <div class="summary-grid">
              <div>
                <span class="summary-label">数据行</span>
                <strong>{{ row.result.data_row_count }}</strong>
              </div>
              <div>
                <span class="summary-label">字段数</span>
                <strong>{{ row.result.column_count }}</strong>
              </div>
              <div>
                <span class="summary-label">重复行</span>
                <strong>{{ row.result.duplicate_rows }}</strong>
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
              <div class="detail-title">字段概览</div>
              <el-table :data="fieldRows(row.result)" size="small" border>
                <el-table-column prop="name" label="字段" min-width="160" />
                <el-table-column prop="type" label="推断类型" width="120" />
                <el-table-column prop="empty" label="空值数" width="100" />
              </el-table>
            </div>

            <div class="field-section" v-if="row.result.preview?.length">
              <div class="detail-title">数据预览</div>
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
        <template #default="{ row }">{{ row.filename || '—' }}</template>
      </el-table-column>
      <el-table-column label="规模" width="140">
        <template #default="{ row }">
          <span v-if="row.result">{{ row.result.data_row_count }} 行 / {{ row.result.column_count }} 列</span>
          <span v-else>—</span>
        </template>
      </el-table-column>
      <el-table-column label="风险提示" min-width="180">
        <template #default="{ row }">
          <el-tag v-if="row.result?.warnings?.length" type="warning" size="small">
            {{ row.result.warnings.length }} 项
          </el-tag>
          <span v-else>—</span>
        </template>
      </el-table-column>
      <el-table-column label="创建者" width="120">
        <template #default="{ row }">{{ row.username || '—' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="dbStatusTag(row.status)" size="small">{{ dbStatusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="提交时间" width="170">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
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

    <div v-if="activeTasks.length === 0 && historyTasks.length === 0 && !tableLoading" class="empty-state">
      <el-empty description="暂无任务，点击上方按钮创建" />
    </div>
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

const statusLabel = (s) => {
  const map = { submitting:'提交中', submit_failed:'提交失败', pending:'排队中', running:'检查中', success:'已完成', failed:'失败', timeout:'超时', not_found:'任务丢失', query_error:'查询异常' }
  return map[s] || s
}
const statusTag = (s) => {
  const map = { submitting:'info', submit_failed:'danger', pending:'info', running:'warning', success:'success', failed:'danger', timeout:'warning', not_found:'warning', query_error:'info' }
  return map[s] || 'info'
}
const dbStatusLabel = (s) => {
  const map = { pending:'排队中', running:'检查中', success:'已完成', failed:'失败' }
  return map[s] || s
}
const dbStatusTag = (s) => {
  const map = { pending:'info', running:'warning', success:'success', failed:'danger' }
  return map[s] || 'info'
}
function formatTime(iso) { return iso ? new Date(iso).toLocaleString('zh-CN') : '' }

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
    const task = { ...data.data, frontendStatus: 'pending', pollCount: 0, pollTimer: null, elapsed: 0, elapsedTimer: null }
    activeTasks.value.unshift(task)
    startPolling(task)
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
  const task = { id: taskId, task_name: submittedName, filename: submittedFilename, frontendStatus: 'submitting', pollCount: 0, pollTimer: null, elapsed: 0, elapsedTimer: null, error: '' }
  activeTasks.value.unshift(task)
  submitting.value = true

  try {
    const { data } = await submitCsvQuality(submittedName, submittedFile)
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
      const { data } = await getCsvQuality(task.id)
      const s = data.data.status
      if (s === 'success' || s === 'failed') {
        stopPolling(task)
        activeTasks.value = activeTasks.value.filter(t => t.id !== task.id)
        historyTasks.value.unshift(data.data)
        total.value++
        if (s === 'success') ElMessage.success('检查完成')
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
.csv-quality-management { max-width: 1200px; margin: 0 auto; }
.top-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.page-title { display: flex; align-items: center; gap: 10px; }
.page-title h2 { margin: 0; font-weight: 600; color: var(--el-text-color-primary); }
.page-icon { font-size: 22px; color: var(--taiji-accent); }
.section-title { margin: 0 0 12px; color: var(--el-text-color-regular); font-size: 14px; font-weight: 500; letter-spacing: 1px; }
.result-card { margin-bottom: 12px; }
.card-header { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.card-title-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 70%; font-size: 13px; color: var(--el-text-color-regular); }
.elapsed-time { color: var(--el-text-color-secondary); font-size: 12px; margin-top: 8px; }
.history-table { width: 100%; border-radius: var(--taiji-radius-sm); overflow: hidden; }
.result-detail { padding: 8px 20px 18px; }
.summary-grid { display: grid; grid-template-columns: repeat(3, minmax(120px, 1fr)); gap: 12px; margin-bottom: 12px; }
.summary-grid > div { background: var(--el-fill-color-lighter); border: 1px solid var(--el-border-color-lighter); border-radius: var(--taiji-radius-sm); padding: 12px; }
.summary-label { display: block; color: var(--el-text-color-secondary); font-size: 12px; margin-bottom: 6px; }
.warning-alert { margin-bottom: 14px; }
.field-section { margin-top: 14px; }
.detail-title { font-size: 13px; font-weight: 600; color: var(--el-text-color-primary); margin-bottom: 8px; }
.csv-upload { width: 100%; }
.upload-icon { font-size: 32px; color: var(--el-text-color-secondary); margin-bottom: 8px; }
.pagination { margin-top: 16px; justify-content: center; }
.empty-state { padding: 60px 0; }
@media (max-width: 760px) {
  .top-bar { align-items: stretch; flex-direction: column; gap: 12px; }
  .summary-grid { grid-template-columns: 1fr; }
}
</style>
