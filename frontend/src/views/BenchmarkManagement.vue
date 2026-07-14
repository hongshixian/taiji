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
        <span class="t-eyebrow">累计任务</span>
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
              @change="onSuiteChange"
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
          <el-alert
            v-if="selectedSuite?.notes"
            :title="selectedSuite.notes"
            type="info"
            :closable="false"
            show-icon
            class="form-alert"
          />
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
          <p class="form-hint">
            <el-icon><InfoFilled /></el-icon>
            生成参数（temperature / max_tokens 等）来自模型管理页面，本次评测将使用其固定值。
          </p>
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
          <p class="form-hint">
            <el-icon><InfoFilled /></el-icon>
            该评测集需要一个模型作为评委来判断答案质量。
          </p>
        </div>

        <div class="form-section">
          <div class="form-section__title">执行控制</div>
          <el-form-item label="样本数量">
            <el-radio-group v-model="limitPreset" @change="onLimitPresetChange">
              <el-radio-button value="20">快速冒烟 (20)</el-radio-button>
              <el-radio-button value="200">标准 (200)</el-radio-button>
              <el-radio-button value="full">完整</el-radio-button>
              <el-radio-button value="custom">自定义</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="limitPreset === 'custom'" label="自定义样本数">
            <el-input-number v-model="form.executionConfig.limit" :min="1" :max="20000" />
          </el-form-item>
          <el-collapse>
            <el-collapse-item title="高级 (并发 / 重复次数 / 超时)" name="adv">
              <div class="adv-grid">
                <el-form-item label="并发数">
                  <el-input-number v-model="form.executionConfig.max_connections" :min="1" :max="100" controls-position="right" />
                </el-form-item>
                <el-form-item label="重复次数">
                  <el-input-number v-model="form.executionConfig.epochs" :min="1" :max="10" controls-position="right" />
                </el-form-item>
                <el-form-item label="超时(分钟)">
                  <el-input-number v-model="form.executionConfig.timeout_minutes" :min="5" :max="720" controls-position="right" />
                </el-form-item>
              </div>
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
        <h2 class="section-card__title">进行中</h2>
      </div>
      <div class="active-list__grid">
        <div v-for="t in activeTasks" :key="t.id" class="active-card">
          <div class="active-card__row">
            <span class="active-card__name">{{ t.task_name || '(未命名)' }}</span>
            <StatusPill :tone="statusTone(t.status)" :label="statusLabel(t.status)" dot />
          </div>
          <div class="active-card__meta">
            <span>{{ suiteLabel(t.benchmark_suite) }}</span>
            <span>{{ modelLabel(t.target_model) }}</span>
          </div>
          <el-progress
            v-if="t.progress && t.progress.total"
            :percentage="Math.round((t.progress.completed / t.progress.total) * 100)"
            :stroke-width="8"
          />
          <div v-else class="active-card__hint">
            {{ t.status === 'pending' ? '等待 Worker 拾取…' : '准备中…' }}
          </div>
        </div>
      </div>
    </section>

    <!-- ========== 历史记录 ========== -->
    <section class="section-card">
      <div class="section-card__header">
        <h2 class="section-card__title">历史记录</h2>
        <el-button size="small" :loading="loading" @click="loadTasks">刷新</el-button>
      </div>

      <el-empty
        v-if="!loading && !historyTasks.length"
        description="还没有已完成的评测任务"
      >
        <el-button type="primary" @click="openCreateDialog">新建测评</el-button>
      </el-empty>

      <template v-else>
        <el-table
          :data="historyTasks"
          v-loading="loading"
          row-key="id"
          :expand-row-keys="expandedKeys"
          style="width:100%"
          @expand-change="onExpandChange"
        >
          <el-table-column type="expand">
            <template #default="{ row }">
              <div class="expand-body">
                <BenchmarkResultCard :task="row" @view-log="openLog(row.id)" />
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="task_name" label="任务" min-width="200" show-overflow-tooltip />
          <el-table-column label="评测集" min-width="180">
            <template #default="{ row }">{{ suiteLabel(row.benchmark_suite) }}</template>
          </el-table-column>
          <el-table-column label="被测模型" min-width="150">
            <template #default="{ row }">{{ modelLabel(row.target_model) }}</template>
          </el-table-column>
          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <StatusPill :tone="statusTone(row.status)" :label="statusLabel(row.status)" />
            </template>
          </el-table-column>
          <el-table-column label="主指标" width="140">
            <template #default="{ row }">
              <span v-if="primaryMetric(row)" class="t-mono">{{ primaryMetric(row) }}</span>
              <span v-else class="muted">—</span>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="170">
            <template #default="{ row }">{{ fmtTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <el-button text size="small" @click="openLog(row.id)">日志</el-button>
              <el-button text type="primary" size="small" @click="onRetry(row.id)">重试</el-button>
              <el-button
                v-if="canDelete"
                text type="danger" size="small"
                @click="onDelete(row.id)"
              >删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-pagination
          :current-page="page"
          :page-size="perPage"
          :total="total"
          background
          layout="total, prev, pager, next, jumper"
          @current-change="onPageChange"
          class="pagination"
        />
      </template>
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
import StatusPill from '../components/StatusPill.vue'
import { usePermission } from '../composables/usePermission'
import { taskStatusTone as statusTone, taskStatusLabel as statusLabel } from '../composables/taskStatus'

const { has } = usePermission()
const canDelete = computed(() => has('task:delete:any'))

// ---- state ----
const showDialog = ref(false)
const submitting = ref(false)
const loading = ref(false)
const tasks = ref([])            // 当前页所有任务（含进行中）
const modelPresets = ref([])
const suites = ref([])
const page = ref(1)
const perPage = ref(10)
const total = ref(0)
const logDialogVisible = ref(false)
const logTaskId = ref(null)
const expandedKeys = ref([])     // 受控展开态，与数据解耦

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
const limitPreset = ref('20')

// ---- computed ----
const enabledSuites = computed(() => suites.value.filter((s) => !s.disabled))
const selectedSuite = computed(() => suites.value.find((s) => s.key === form.suiteKey) || null)
const activeTasks = computed(() =>
  tasks.value.filter((t) => t.status === 'pending' || t.status === 'running'),
)
const historyTasks = computed(() =>
  tasks.value.filter((t) => t.status === 'success' || t.status === 'failed'),
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
    mergeById(data.data.items || [])
    total.value = data.data.total || 0
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '加载任务失败')
  } finally {
    loading.value = false
  }
}

// 按 id 就地合并，保留未变化行的对象引用（配合 row-key 保留展开态、避免闪烁）
function mergeById(incoming) {
  const byId = new Map(tasks.value.map((t) => [t.id, t]))
  const next = incoming.map((item) => {
    const existing = byId.get(item.id)
    if (existing) {
      Object.assign(existing, item)
      return existing
    }
    return item
  })
  tasks.value = next
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
  const active = activeTasks.value
  if (!active.length) return
  let anySettled = false
  for (const t of active) {
    try {
      const { data } = await getBenchmark(t.id)
      Object.assign(t, data.data)   // 就地更新，引用不变
      if (t.status === 'success' || t.status === 'failed') anySettled = true
    } catch (e) {
      // silent
    }
  }
  // 有任务完成时，静默重新拉一次列表以校正总数/排序（就地合并，不影响展开）
  if (anySettled) loadTasks()
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
  limitPreset.value = '20'
  showDialog.value = true
}

function onSuiteChange() {
  // 切换 suite 时：不需要评委则清空 judge；重置 suite 特有参数
  if (!selectedSuite.value?.needs_judge) {
    form.judgeModelId = null
  }
  form.suiteConfig = {}
}

function onLimitPresetChange(v) {
  if (v === 'custom') {
    form.executionConfig.limit = form.executionConfig.limit ?? 100
  } else if (v === 'full') {
    form.executionConfig.limit = null
  } else {
    form.executionConfig.limit = Number(v)
  }
}

async function onSubmit() {
  if (!form.taskName.trim()) return ElMessage.warning('请填写任务名称')
  if (!form.suiteKey) return ElMessage.warning('请选择评测集')
  if (!form.targetModelId) return ElMessage.warning('请选择被测模型')
  const needsJudge = selectedSuite.value?.needs_judge
  if (needsJudge && !form.judgeModelId) {
    return ElMessage.warning('该评测集需要评委模型')
  }

  submitting.value = true
  try {
    await submitBenchmark({
      task_name: form.taskName.trim(),
      notes: form.notes.trim() || null,
      benchmark_suite: form.suiteKey,
      target_model_id: form.targetModelId,
      judge_model_id: needsJudge ? form.judgeModelId : null,
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
    expandedKeys.value = expandedKeys.value.filter((k) => k !== id)
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

function onExpandChange(row, expandedRows) {
  // 受控维护展开集合
  expandedKeys.value = expandedRows.map((r) => r.id)
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

function primaryMetric(row) {
  const metrics = row.result?.metrics
  if (!metrics || !Object.keys(metrics).length) return null
  // 优先展示 accuracy，否则取第一个
  const key = 'accuracy' in metrics ? 'accuracy' : Object.keys(metrics)[0]
  const v = metrics[key]
  const val = typeof v === 'number' ? (Number.isInteger(v) ? v : v.toFixed(4)) : v
  return `${key}: ${val}`
}

function fmtTime(t) {
  if (!t) return '—'
  return new Date(t).toLocaleString()
}
</script>

<style scoped>
.page-header__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-6);
}

.metric-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--space-5);
  margin-bottom: var(--space-8);
}
.metric {
  background: var(--bg-surface-sunken);
  padding: var(--space-6);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.metric-value {
  font-size: var(--text-3xl);
  font-weight: var(--weight-bold);
  color: var(--fg-primary);
}

/* form */
.form-section {
  margin-bottom: var(--space-7);
  padding-bottom: var(--space-6);
  border-bottom: 1px dashed var(--border-subtle);
}
.form-section:last-child { border-bottom: none; margin-bottom: 0; }
.form-section__title {
  font-weight: var(--weight-semibold);
  margin-bottom: var(--space-5);
  color: var(--fg-primary);
}
.form-hint {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--fg-tertiary);
  font-size: var(--text-xs);
  margin: var(--space-3) 0 0;
}
.form-alert { margin-top: var(--space-3); }
.adv-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 0 var(--space-6);
}

.suite-badge {
  font-size: var(--text-xs);
  color: var(--fg-tertiary);
  margin-left: var(--space-4);
  font-family: var(--font-mono);
}
.suite-badge--disabled { color: var(--color-warning-fg); }

/* active list */
.active-list { margin-bottom: var(--space-8); }
.active-list__header { margin-bottom: var(--space-5); }
.active-list__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: var(--space-5);
}
.active-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  box-shadow: var(--shadow-xs);
  padding: var(--space-6);
  border-radius: var(--radius-lg);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.active-card__row { display: flex; justify-content: space-between; align-items: center; gap: var(--space-4); }
.active-card__name { font-weight: var(--weight-semibold); color: var(--fg-primary); }
.active-card__meta { display: flex; gap: var(--space-5); color: var(--fg-tertiary); font-size: var(--text-xs); }
.active-card__hint { font-size: var(--text-xs); color: var(--fg-tertiary); }

.expand-body { padding: var(--space-4) var(--space-6); }
.pagination { margin-top: var(--space-6); justify-content: flex-end; }
.muted { color: var(--fg-tertiary); }

@media (max-width: 768px) {
  .page-header__row { flex-direction: column; align-items: flex-start; }
}
</style>
