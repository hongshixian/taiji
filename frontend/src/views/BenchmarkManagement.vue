<template>
  <div class="page-shell benchmark-task">
    <header class="page-header">
      <span class="page-header__eyebrow t-eyebrow">任务 · Benchmark 测评</span>
      <div class="page-header__row">
        <h1 class="page-header__title">Benchmark 测评</h1>
        <el-button type="primary" @click="openCreateDialog">
          <el-icon><Plus /></el-icon>&nbsp;新建测评
        </el-button>
      </div>
      <p class="page-header__lede">
        选择被测模型与评测集，由 Worker 异步驱动 inspect_evals 引擎执行标准化 Benchmark 评测。
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
        <span class="t-eyebrow">可用评测集</span>
        <span class="t-mono metric-value">{{ enabledSuites.length }}</span>
      </div>
    </section>

    <!-- ========== 新建测评对话框 ========== -->
    <el-dialog
      v-model="showDialog"
      title="新建 Benchmark 测评"
      width="720px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="formRef"
        :model="form"
        label-width="120px"
        label-position="right"
        @submit.prevent
      >
        <div class="form-section">
          <div class="form-section__title">基本信息</div>
          <el-form-item label="任务名称" required>
            <el-input
              v-model="form.taskName"
              placeholder="例：GPT-4o MMLU 测评"
              maxlength="100"
              show-word-limit
            />
          </el-form-item>
          <el-form-item label="备注">
            <el-input
              v-model="form.notes"
              type="textarea"
              :rows="2"
              placeholder="记录本次评测的目的（可选）"
              maxlength="500"
              show-word-limit
            />
          </el-form-item>
        </div>

        <div class="form-section">
          <div class="form-section__title">评测集</div>
          <el-form-item label="Benchmark" required>
            <el-select
              v-model="form.suiteKey"
              placeholder="请选择评测集"
              filterable
              style="width:100%"
            >
              <el-option-group
                v-for="grp in suiteGroups"
                :key="grp.category"
                :label="grp.label"
              >
                <el-option
                  v-for="s in grp.suites"
                  :key="s.key"
                  :label="s.display_name"
                  :value="s.key"
                  :disabled="s.disabled"
                >
                  <span>{{ s.display_name }}</span>
                  <span class="suite-badge">{{ s.key }}</span>
                  <span v-if="s.disabled" class="suite-badge suite-badge--disabled">
                    {{ s.disabled_reason || '禁用' }}
                  </span>
                </el-option>
              </el-option-group>
            </el-select>
          </el-form-item>
          <div v-if="selectedSuite?.notes" class="form-tip">
            <el-icon><InfoFilled /></el-icon>&nbsp;{{ selectedSuite.notes }}
          </div>
        </div>

        <div class="form-section">
          <div class="form-section__title">被测模型</div>
          <el-form-item label="模型" required>
            <el-select
              v-model="form.targetModelId"
              placeholder="选择已配置的模型"
              filterable
              style="width:100%"
            >
              <el-option
                v-for="m in modelPresets"
                :key="m.id"
                :label="m.display_name"
                :value="m.id"
              >
                <span>{{ m.display_name }}</span>
                <span class="suite-badge">{{ m.api_protocol }}</span>
              </el-option>
            </el-select>
          </el-form-item>
          <div class="form-tip">
            <el-icon><InfoFilled /></el-icon>&nbsp;
            生成参数（temperature / max_tokens 等）来自模型管理页面，本次评测将使用其固定值。
          </div>
        </div>

        <div v-if="selectedSuite?.needs_judge" class="form-section">
          <div class="form-section__title">评委模型</div>
          <el-form-item label="模型" required>
            <el-select
              v-model="form.judgeModelId"
              placeholder="选择评委模型"
              filterable
              style="width:100%"
            >
              <el-option
                v-for="m in modelPresets"
                :key="m.id"
                :label="m.display_name"
                :value="m.id"
              >
                <span>{{ m.display_name }}</span>
                <span class="suite-badge">{{ m.api_protocol }}</span>
              </el-option>
            </el-select>
          </el-form-item>
        </div>

        <div class="form-section">
          <div class="form-section__title">执行控制</div>
          <el-form-item label="样本数量">
            <el-radio-group v-model="limitPreset" @change="onLimitPresetChange">
              <el-radio-button :label="20">快速冒烟 (20)</el-radio-button>
              <el-radio-button :label="200">标准 (200)</el-radio-button>
              <el-radio-button :label="null">完整</el-radio-button>
              <el-radio-button label="custom">自定义</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="limitPreset === 'custom'" label="自定义样本数">
            <el-input-number v-model="form.executionConfig.limit" :min="1" :max="20000" />
          </el-form-item>
          <el-collapse>
            <el-collapse-item title="高级 (并发 / 重复次数 / 超时)" name="adv">
              <el-form-item label="并发数">
                <el-input-number v-model="form.executionConfig.max_connections" :min="1" :max="100" />
              </el-form-item>
              <el-form-item label="重复次数 (epochs)">
                <el-input-number v-model="form.executionConfig.epochs" :min="1" :max="10" />
              </el-form-item>
              <el-form-item label="超时（分钟）">
                <el-input-number v-model="form.executionConfig.timeout_minutes" :min="5" :max="720" />
              </el-form-item>
            </el-collapse-item>
          </el-collapse>
        </div>

        <div v-if="selectedSuite?.config_schema?.fields?.length" class="form-section">
          <div class="form-section__title">Suite 特有参数</div>
          <DynamicField
            v-for="field in selectedSuite.config_schema.fields"
            :key="field.key"
            :field="field"
            v-model="form.suiteConfig[field.key]"
          />
        </div>
      </el-form>

      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="onSubmit">提交任务</el-button>
      </template>
    </el-dialog>

    <!-- ========== 进行中任务 ========== -->
    <section v-if="activeTasks.length" class="active-list">
      <div class="active-list__header">
        <h2 class="section-title">进行中</h2>
      </div>
      <div class="active-list__grid">
        <div v-for="t in activeTasks" :key="t.tempId || t.id" class="active-card">
          <div class="active-card__row">
            <span class="active-card__name">{{ t.task_name || '(未命名)' }}</span>
            <span class="status-pill" :data-tone="statusTone(t.status)">{{ statusLabel(t.status) }}</span>
          </div>
          <div class="active-card__meta">
            <span>{{ suiteLabel(t.benchmark_suite) }}</span>
            <span>{{ modelLabel(t.target_model) }}</span>
          </div>
          <el-progress
            v-if="t.progress && t.progress.total"
            :percentage="Math.round((t.progress.completed / t.progress.total) * 100)"
            :stroke-width="6"
            :show-text="true"
          />
          <div v-else class="active-card__hint">
            {{ t.status === 'pending' ? '等待 Worker 拾取…' : '准备中…' }}
          </div>
        </div>
      </div>
    </section>

    <!-- ========== 历史记录 ========== -->
    <section class="settings-card">
      <div class="settings-card__header">
        <h2 class="section-title">历史记录</h2>
        <el-button size="small" @click="loadTasks">刷新</el-button>
      </div>
      <el-table :data="tasks" v-loading="loading" style="width:100%">
        <el-table-column type="expand">
          <template #default="{ row }">
            <BenchmarkResultCard :task="row" @view-log="openLog(row.id)" />
          </template>
        </el-table-column>
        <el-table-column prop="task_name" label="任务" min-width="200" />
        <el-table-column label="评测集" min-width="180">
          <template #default="{ row }">{{ suiteLabel(row.benchmark_suite) }}</template>
        </el-table-column>
        <el-table-column label="被测模型" min-width="160">
          <template #default="{ row }">{{ modelLabel(row.target_model) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <span class="status-pill" :data-tone="statusTone(row.status)">{{ statusLabel(row.status) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="进度" width="120">
          <template #default="{ row }">
            <span v-if="row.progress?.total" class="t-mono">
              {{ row.progress.completed }}/{{ row.progress.total }}
            </span>
            <span v-else>—</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">{{ fmtTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openLog(row.id)">日志</el-button>
            <el-button
              size="small"
              type="primary"
              :disabled="row.status === 'running'"
              @click="onRetry(row.id)"
            >重试</el-button>
            <el-button
              v-if="canDelete"
              size="small"
              type="danger"
              @click="onDelete(row.id)"
            >删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        :current-page="page"
        :page-size="perPage"
        :total="total"
        layout="prev, pager, next, jumper, total"
        @current-change="onPageChange"
        style="margin-top:1rem;justify-content:flex-end"
      />
    </section>

    <TaskLogDialog v-model:visible="logDialogVisible" :task-id="logTaskId" />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { InfoFilled, Plus } from '@element-plus/icons-vue'

import {
  submitBenchmark,
  getBenchmark,
  listBenchmarks,
  retryBenchmark,
  deleteBenchmark,
  listBenchmarkSuites,
} from '../api/benchmark'
import { listModels } from '../api/model'
import TaskLogDialog from '../components/TaskLogDialog.vue'
import BenchmarkResultCard from '../components/BenchmarkResultCard.vue'
import DynamicField from '../components/DynamicField.vue'
import { usePermission } from '../composables/usePermission'

const { has } = usePermission()
const canDelete = computed(() => has('task:delete:any'))

// ---- state ----
const showDialog = ref(false)
const submitting = ref(false)
const loading = ref(false)
const tasks = ref([])
const activeTasks = ref([])
const modelPresets = ref([])
const suites = ref([])
const page = ref(1)
const perPage = ref(10)
const total = ref(0)
const logDialogVisible = ref(false)
const logTaskId = ref(null)

const form = reactive({
  taskName: '',
  notes: '',
  suiteKey: '',
  targetModelId: null,
  judgeModelId: null,
  executionConfig: {
    limit: 20,
    max_connections: 10,
    epochs: 1,
    timeout_minutes: 60,
  },
  suiteConfig: {},
})
const limitPreset = ref(20)

// ---- computed ----
const enabledSuites = computed(() => suites.value.filter((s) => !s.disabled))
const selectedSuite = computed(() =>
  suites.value.find((s) => s.key === form.suiteKey) || null,
)

const suiteGroups = computed(() => {
  const groups = {
    capability: { category: 'capability', label: '能力评测', suites: [] },
    safety: { category: 'safety', label: '安全评测', suites: [] },
    alignment: { category: 'alignment', label: '对齐/行为评测', suites: [] },
  }
  suites.value.forEach((s) => {
    ;(groups[s.category] || groups.capability).suites.push(s)
  })
  Object.values(groups).forEach((g) => g.suites.sort((a, b) => a.display_name.localeCompare(b.display_name)))
  return Object.values(groups).filter((g) => g.suites.length)
})

// ---- lifecycle ----
let pollTimer = null

onMounted(async () => {
  await Promise.all([loadTasks(), loadModels(), loadSuites()])
  pollTimer = setInterval(pollActive, 2000)
})

onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer)
})

// ---- data loading ----
async function loadTasks() {
  loading.value = true
  try {
    const { data } = await listBenchmarks(page.value, perPage.value)
    tasks.value = data.data.items || []
    total.value = data.data.total || 0
    // 补充进行中列表
    activeTasks.value = tasks.value.filter((t) => t.status === 'pending' || t.status === 'running')
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '加载任务失败')
  } finally {
    loading.value = false
  }
}

async function loadModels() {
  try {
    const { data } = await listModels(1, 200, false)
    modelPresets.value = data.data.items || []
  } catch (e) {
    // ignore
  }
}

async function loadSuites() {
  try {
    const { data } = await listBenchmarkSuites()
    suites.value = data.data.items || []
  } catch (e) {
    ElMessage.error('加载评测集失败')
  }
}

// ---- polling ----
async function pollActive() {
  if (!activeTasks.value.length) return
  const settled = []
  for (const t of activeTasks.value) {
    if (!t.id) continue
    try {
      const { data } = await getBenchmark(t.id)
      Object.assign(t, data.data)
      if (t.status === 'success' || t.status === 'failed') {
        settled.push(t.id)
      }
    } catch (e) {
      // silent
    }
  }
  if (settled.length) loadTasks()
}

// ---- form ----
function openCreateDialog() {
  form.taskName = ''
  form.notes = ''
  form.suiteKey = ''
  form.targetModelId = null
  form.judgeModelId = null
  form.executionConfig = { limit: 20, max_connections: 10, epochs: 1, timeout_minutes: 60 }
  form.suiteConfig = {}
  limitPreset.value = 20
  showDialog.value = true
}

function onLimitPresetChange(v) {
  if (v === 'custom') {
    form.executionConfig.limit = form.executionConfig.limit ?? 100
  } else {
    form.executionConfig.limit = v
  }
}

async function onSubmit() {
  if (!form.taskName.trim()) return ElMessage.warning('请填写任务名称')
  if (!form.suiteKey) return ElMessage.warning('请选择评测集')
  if (!form.targetModelId) return ElMessage.warning('请选择被测模型')
  if (selectedSuite.value?.needs_judge && !form.judgeModelId) {
    return ElMessage.warning('该评测集需要评委模型')
  }

  submitting.value = true
  try {
    await submitBenchmark({
      task_name: form.taskName.trim(),
      notes: form.notes.trim() || null,
      benchmark_suite: form.suiteKey,
      target_model_id: form.targetModelId,
      judge_model_id: form.judgeModelId,
      execution_config: form.executionConfig,
      suite_config: form.suiteConfig,
    })
    ElMessage.success('任务已提交')
    showDialog.value = false
    await loadTasks()
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '提交失败')
  } finally {
    submitting.value = false
  }
}

async function onRetry(id) {
  try {
    await retryBenchmark(id)
    ElMessage.success('已重新提交')
    loadTasks()
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '重试失败')
  }
}

async function onDelete(id) {
  try {
    await ElMessageBox.confirm('确认删除这条评测任务？', '确认', { type: 'warning' })
    await deleteBenchmark(id)
    ElMessage.success('已删除')
    loadTasks()
  } catch (e) {
    if (e === 'cancel') return
    ElMessage.error(e.response?.data?.message || '删除失败')
  }
}

function onPageChange(p) {
  page.value = p
  loadTasks()
}

// ---- log ----
function openLog(id) {
  logTaskId.value = id
  logDialogVisible.value = true
}

// ---- helpers ----
function suiteLabel(key) {
  const s = suites.value.find((x) => x.key === key)
  return s ? s.display_name : key
}

function modelLabel(m) {
  if (!m) return '—'
  return m.display_name || m.model_name || '—'
}

function statusTone(status) {
  return {
    pending: 'warning',
    running: 'info',
    success: 'success',
    failed: 'danger',
  }[status] || 'neutral'
}

function statusLabel(status) {
  return {
    pending: '等待中',
    running: '执行中',
    success: '成功',
    failed: '失败',
  }[status] || status
}

function fmtTime(t) {
  if (!t) return '—'
  return new Date(t).toLocaleString()
}
</script>

<style scoped>
.metric-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--space-3, 12px);
  margin: var(--space-4, 16px) 0;
}
.metric {
  background: var(--color-surface-2, #f7f8fb);
  padding: var(--space-4, 16px);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  gap: var(--space-1, 4px);
}
.metric-value {
  font-size: 24px;
  font-weight: 600;
}

.form-section {
  margin-bottom: var(--space-5, 20px);
  padding-bottom: var(--space-4, 16px);
  border-bottom: 1px dashed var(--color-border-subtle, #eee);
}
.form-section:last-child { border-bottom: none; }
.form-section__title {
  font-weight: 600;
  margin-bottom: var(--space-3, 12px);
  color: var(--color-text-2, #333);
}
.form-tip {
  color: var(--color-text-3, #666);
  font-size: 12px;
  display: flex;
  align-items: center;
  margin-top: 4px;
}

.suite-badge {
  font-size: 11px;
  color: var(--color-text-3, #888);
  margin-left: 8px;
  font-family: var(--font-mono, monospace);
}
.suite-badge--disabled {
  color: var(--color-danger, #e6a23c);
}

.active-list { margin: var(--space-6, 24px) 0; }
.active-list__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-3, 12px);
}
.active-card {
  background: var(--color-surface-2, #f7f8fb);
  padding: var(--space-4, 16px);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  gap: var(--space-2, 8px);
}
.active-card__row { display: flex; justify-content: space-between; align-items: center; }
.active-card__name { font-weight: 600; }
.active-card__meta { display: flex; gap: 12px; color: var(--color-text-3, #666); font-size: 12px; }
.active-card__hint { font-size: 12px; color: var(--color-text-3, #999); }

.settings-card {
  background: var(--color-surface-1, #fff);
  border-radius: 12px;
  padding: var(--space-5, 20px);
  border: 1px solid var(--color-border-subtle, #eef);
}
.settings-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4, 16px);
}
.section-title { font-size: 18px; margin: 0; }

.status-pill {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
  background: var(--color-neutral-100, #eee);
}
.status-pill[data-tone='success'] { background: #e6f7ea; color: #229c53; }
.status-pill[data-tone='danger'] { background: #fdecec; color: #c94040; }
.status-pill[data-tone='warning'] { background: #fff3e0; color: #c97b1e; }
.status-pill[data-tone='info'] { background: #e6f0ff; color: #3670c9; }
</style>
