<template>
  <div class="page-shell page-shell--wide">
    <header class="mb-8 flex flex-col gap-2">
      <span class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">{{ t('benchmark.pageEyebrow') }}</span>
      <div class="flex items-center justify-between gap-6">
        <h1 class="m-0 text-3xl font-bold tracking-tight text-fg">{{ t('benchmark.pageTitle') }}</h1>
        <UiButton @click="openCreateDialog">
          <Plus class="size-4" /> {{ t('benchmark.newTask') }}
        </UiButton>
      </div>
      <p class="m-0 max-w-[64ch] text-sm text-fg-secondary">
        {{ t('benchmark.pageDesc') }}
      </p>
    </header>

    <!-- 指标 -->
    <section class="mb-8 grid grid-cols-[repeat(auto-fit,minmax(180px,1fr))] gap-5">
      <div class="flex flex-col gap-2 rounded-lg border border-line bg-surface-sunken p-6">
        <span class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">{{ t('benchmark.metricActive') }}</span>
        <span class="font-mono text-3xl font-bold text-fg">{{ stats.active }}</span>
      </div>
      <div class="flex flex-col gap-2 rounded-lg border border-line bg-surface-sunken p-6">
        <span class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">{{ t('benchmark.metricTotal') }}</span>
        <span class="font-mono text-3xl font-bold text-fg">{{ stats.total }}</span>
      </div>
      <div class="flex flex-col gap-2 rounded-lg border border-line bg-surface-sunken p-6">
        <span class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">{{ t('benchmark.metricSuites') }}</span>
        <span class="font-mono text-3xl font-bold text-fg">{{ enabledSuites.length }}</span>
      </div>
    </section>

    <!-- 新建对话框 -->
    <UiDialog v-model="showDialog" :title="t('benchmark.dialogTitle')" width="720px">
      <div class="flex flex-col gap-6">
        <section class="flex flex-col gap-4 border-b border-line pb-5">
          <div class="font-semibold text-fg">{{ t('benchmark.sectionBasic') }}</div>
          <UiFormItem :label="t('benchmark.taskName')" inline>
            <UiInput v-model="form.taskName" :placeholder="t('benchmark.taskNamePlaceholder')" :maxlength="100" />
          </UiFormItem>
          <UiFormItem :label="t('benchmark.notes')" inline>
            <UiTextarea v-model="form.notes" :rows="2" :placeholder="t('benchmark.notesPlaceholder')" :maxlength="500" />
          </UiFormItem>
        </section>

        <section class="flex flex-col gap-4 border-b border-line pb-5">
          <div class="font-semibold text-fg">{{ t('benchmark.sectionSuite') }}</div>
          <UiFormItem label="Benchmark" required inline>
            <UiSelect
              v-model="form.suiteKey"
              :groups="suiteSelectGroups"
              :placeholder="t('benchmark.suitePlaceholder')"
              filterable
              @update:model-value="onSuiteChange"
            />
          </UiFormItem>
          <UiAlert v-if="selectedSuite?.notes" type="info" :title="selectedSuite.notes" />
        </section>

        <section class="flex flex-col gap-4 border-b border-line pb-5">
          <div class="font-semibold text-fg">{{ t('benchmark.sectionTarget') }}</div>
          <UiFormItem :label="t('benchmark.model')" required inline>
            <UiSelect v-model="form.targetModelId" :options="modelOptions" :placeholder="t('benchmark.targetModelPlaceholder')" filterable />
          </UiFormItem>
          <p class="flex items-center gap-2 text-xs text-fg-tertiary">
            <Info class="size-4" /> {{ t('benchmark.targetModelHint') }}
          </p>
        </section>

        <section v-if="selectedSuite?.needs_judge" class="flex flex-col gap-4 border-b border-line pb-5">
          <div class="font-semibold text-fg">{{ t('benchmark.sectionJudge') }}</div>
          <UiFormItem :label="t('benchmark.model')" required inline>
            <UiSelect v-model="form.judgeModelId" :options="modelOptions" :placeholder="t('benchmark.judgeModelPlaceholder')" filterable />
          </UiFormItem>
          <p class="flex items-center gap-2 text-xs text-fg-tertiary">
            <Info class="size-4" /> {{ t('benchmark.judgeModelHint') }}
          </p>
        </section>

        <section class="flex flex-col gap-4 border-b border-line pb-5">
          <div class="font-semibold text-fg">{{ t('benchmark.sectionExecution') }}</div>
          <UiFormItem :label="t('benchmark.sampleCount')" inline>
            <UiSegmented v-model="limitPreset" :options="limitPresetOptions" @update:model-value="onLimitPresetChange" />
          </UiFormItem>
          <UiFormItem v-if="limitPreset === 'custom'" :label="t('benchmark.customSampleCount')" inline>
            <UiInputNumber v-model="form.executionConfig.limit" :min="1" :max="20000" />
          </UiFormItem>
          <UiCollapse :title="t('benchmark.advanced')">
            <div class="grid grid-cols-[repeat(auto-fit,minmax(180px,1fr))] gap-4">
              <UiFormItem :label="t('benchmark.maxConnections')"><UiInputNumber v-model="form.executionConfig.max_connections" :min="1" :max="100" block /></UiFormItem>
              <UiFormItem :label="t('benchmark.epochs')"><UiInputNumber v-model="form.executionConfig.epochs" :min="1" :max="10" block /></UiFormItem>
              <UiFormItem :label="t('benchmark.timeoutMinutes')"><UiInputNumber v-model="form.executionConfig.timeout_minutes" :min="5" :max="720" block /></UiFormItem>
            </div>
          </UiCollapse>
        </section>

        <section v-if="selectedSuite?.config_schema?.fields?.length" class="flex flex-col gap-4">
          <div class="font-semibold text-fg">{{ t('benchmark.suiteParams') }}</div>
          <DynamicField
            v-for="field in selectedSuite.config_schema.fields"
            :key="field.key"
            :field="field"
            v-model="form.suiteConfig[field.key]"
          />
        </section>
      </div>

      <template #footer>
        <UiButton variant="secondary" @click="showDialog = false">{{ t('common.cancel') }}</UiButton>
        <UiButton :loading="submitting" @click="onSubmit">{{ t('benchmark.submitTask') }}</UiButton>
      </template>
    </UiDialog>

    <!-- 任务列表（全部状态） -->
    <section class="rounded-lg border border-line bg-surface p-6">
      <div class="mb-6 flex items-center justify-between">
        <h2 class="text-lg font-semibold text-fg">{{ t('benchmark.taskList') }}</h2>
        <UiButton variant="secondary" size="sm" :loading="loading" @click="loadTasks">{{ t('common.refresh') }}</UiButton>
      </div>

      <UiEmpty v-if="!loading && !tasks.length" :description="t('benchmark.emptyTasks')">
        <UiButton @click="openCreateDialog">{{ t('benchmark.newTask') }}</UiButton>
      </UiEmpty>

      <template v-else>
        <UiTable
          :columns="columns"
          :data="tasks"
          row-key="id"
          expandable
          :expanded-keys="expandedKeys"
          :loading="loading"
          @update:expanded-keys="onExpand"
        >
          <template #cell-benchmark_suite="{ row }">{{ suiteLabel(row.benchmark_suite) }}</template>
          <template #cell-target_model="{ row }">{{ modelLabel(row.target_model) }}</template>
          <template #cell-status="{ row }">
            <StatusPill :tone="statusTone(row.status)" :label="statusLabel(row.status)" />
          </template>
          <template #cell-progress="{ row }">
            <span v-if="row.progress && row.progress.total" class="font-mono text-xs text-fg-secondary">
              {{ row.progress.completed }}/{{ row.progress.total }}
            </span>
            <span v-else class="text-fg-tertiary">—</span>
          </template>
          <template #cell-metric="{ row }">
            <span v-if="primaryMetric(row)" class="font-mono">{{ primaryMetric(row) }}</span>
            <span v-else class="text-fg-tertiary">—</span>
          </template>
          <template #cell-created_at="{ row }">{{ fmtTime(row.created_at) }}</template>
          <template #cell-actions="{ row }">
            <div class="flex items-center gap-1">
              <UiButton variant="text" size="sm" @click="openLog(row.id)">{{ t('benchmark.log') }}</UiButton>
              <!-- 进行中/等待中：停止（等待中不可点） -->
              <UiButton
                v-if="row.status === 'running' || row.status === 'pending'"
                variant="text" size="sm"
                :disabled="row.status === 'pending'"
                @click="onStop(row.id)"
              >{{ t('benchmark.stop') }}</UiButton>
              <!-- 失败/已停止：可重试 -->
              <UiButton
                v-if="row.status === 'failed' || row.status === 'stopped'"
                variant="text" size="sm"
                @click="onRetry(row.id)"
              >{{ t('common.retry') }}</UiButton>
              <UiButton v-if="canDelete" variant="danger-text" size="sm" @click="onDelete(row.id)">{{ t('common.delete') }}</UiButton>
            </div>
          </template>
          <template #expand="{ row }">
            <BenchmarkResultCard :task="row" @view-log="openLog(row.id)" />
          </template>
        </UiTable>
        <div class="mt-6 flex justify-end">
          <UiPagination :current-page="page" :page-size="perPage" :total="total" @current-change="onPageChange" />
        </div>
      </template>
    </section>

    <TaskLogDialog v-model:visible="logDialogVisible" :task-id="logTaskId" />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Plus, Info } from 'lucide-vue-next'
import { toast } from '@/lib/toast'
import { confirm } from '@/lib/confirm'
import {
  submitBenchmark,
  getBenchmark,
  listBenchmarks,
  getBenchmarkStats,
  retryBenchmark,
  deleteBenchmark,
  stopBenchmark,
  listEnabledBenchmarkSuites,
} from '@/api/benchmark'
import { listModels } from '@/api/model'
import type { BenchmarkTask, BenchmarkStats, SuiteDescriptor, ModelConfig } from '@/api/types'
import TaskLogDialog from '@/components/TaskLogDialog.vue'
import BenchmarkResultCard from '@/components/BenchmarkResultCard.vue'
import DynamicField from '@/components/DynamicField.vue'
import StatusPill from '@/components/StatusPill.vue'
import UiButton from '@/components/ui/Button.vue'
import UiInput from '@/components/ui/Input.vue'
import UiTextarea from '@/components/ui/Textarea.vue'
import UiInputNumber from '@/components/ui/InputNumber.vue'
import UiSelect, { type SelectOption, type SelectGroupDef } from '@/components/ui/Select.vue'
import UiDialog from '@/components/ui/Dialog.vue'
import UiFormItem from '@/components/ui/FormItem.vue'
import UiAlert from '@/components/ui/Alert.vue'
import UiCollapse from '@/components/ui/Collapse.vue'
import UiSegmented from '@/components/ui/SegmentedControl.vue'
import UiProgress from '@/components/ui/Progress.vue'
import UiEmpty from '@/components/ui/Empty.vue'
import UiTable, { type TableColumn } from '@/components/ui/Table.vue'
import UiPagination from '@/components/ui/Pagination.vue'
import { usePermission } from '@/composables/usePermission'
import { taskStatusTone as statusTone, taskStatusLabel as statusLabel } from '@/composables/taskStatus'

const { has } = usePermission()
const { t } = useI18n()
const canDelete = computed(() => has('task:delete:any'))

const showDialog = ref(false)
const submitting = ref(false)
const loading = ref(false)
const tasks = ref<BenchmarkTask[]>([])
const modelPresets = ref<ModelConfig[]>([])
const suites = ref<SuiteDescriptor[]>([])
const page = ref(1)
const perPage = ref(10)
const total = ref(0)
// 顶部指标（全局口径，由 /stats 驱动，不依赖当前分页）
const stats = ref<BenchmarkStats>({ pending: 0, running: 0, success: 0, failed: 0, stopped: 0, active: 0, total: 0 })
const logDialogVisible = ref(false)
const logTaskId = ref<number | null>(null)
const expandedKeys = ref<(string | number)[]>([])

const form = reactive({
  taskName: '',
  notes: '',
  suiteKey: '' as string,
  targetModelId: null as number | null,
  judgeModelId: null as number | null,
  executionConfig: { limit: 20 as number | null, max_connections: 10, epochs: 1, timeout_minutes: 60 },
  suiteConfig: {} as Record<string, unknown>,
})
const limitPreset = ref<string | number | null>('20')

const limitPresetOptions = computed(() => [
  { label: t('benchmark.presetSmoke'), value: '20' },
  { label: t('benchmark.presetStandard'), value: '200' },
  { label: t('benchmark.presetFull'), value: 'full' },
  { label: t('benchmark.presetCustom'), value: 'custom' },
])

const columns = computed<TableColumn[]>(() => [
  { key: 'task_name', label: t('benchmark.colTask'), minWidth: 180, tooltip: true },
  { key: 'benchmark_suite', label: t('benchmark.colSuite'), minWidth: 160, tooltip: true },
  { key: 'target_model', label: t('benchmark.colTargetModel'), minWidth: 130, tooltip: true },
  { key: 'status', label: t('common.status'), width: 100 },
  { key: 'progress', label: t('benchmark.colProgress'), width: 90 },
  { key: 'metric', label: t('benchmark.colMetric'), width: 120 },
  { key: 'created_at', label: t('common.createdAt'), width: 160 },
  { key: 'actions', label: t('common.actions'), width: 200, fixed: 'right' },
])

const enabledSuites = computed(() => suites.value.filter((s) => !s.disabled))
const selectedSuite = computed(() => suites.value.find((s) => s.key === form.suiteKey) || null)
// 当前页里未终结的任务（用于轮询刷新进度/状态）
const activeTasks = computed(() => tasks.value.filter((t) => t.status === 'pending' || t.status === 'running'))

const modelOptions = computed<SelectOption[]>(() =>
  modelPresets.value.map((m) => ({ label: m.display_name, value: m.id, badge: m.api_protocol })),
)

const suiteSelectGroups = computed<SelectGroupDef[]>(() => {
  const groups: Record<string, { label: string; options: SelectOption[] }> = {
    capability: { label: t('benchmark.categoryCapability'), options: [] },
    safety: { label: t('benchmark.categorySafety'), options: [] },
    alignment: { label: t('benchmark.categoryAlignment'), options: [] },
  }
  suites.value.forEach((s) => {
    ;(groups[s.category] || groups.capability).options.push({
      label: s.display_name,
      value: s.key,
      disabled: s.disabled,
      badge: s.key,
    })
  })
  return Object.values(groups).filter((g) => g.options.length)
})

let pollTimer: ReturnType<typeof setInterval> | null = null
onMounted(async () => {
  await Promise.all([loadTasks(), loadModels(), loadSuites(), loadStats()])
  // 每 2s 统一刷新：全局指标(stats) + 当前页进行中任务的进度/状态
  pollTimer = setInterval(tick, 2000)
})
onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer)
})

async function loadTasks() {
  loading.value = true
  try {
    const { data } = await listBenchmarks(page.value, perPage.value)
    mergeById(data.data.items || [])
    total.value = data.data.total || 0
  } catch (err: unknown) {
    toast.error(errMsg(err) || t('benchmark.loadTasksFailed'))
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  try {
    const { data } = await getBenchmarkStats()
    stats.value = data.data
  } catch { /* silent */ }
}

function mergeById(incoming: BenchmarkTask[]) {
  const byId = new Map(tasks.value.map((t) => [t.id, t]))
  tasks.value = incoming.map((item) => {
    const existing = byId.get(item.id)
    if (existing) {
      Object.assign(existing, item)
      return existing
    }
    return item
  })
}

async function loadModels() {
  try {
    const { data } = await listModels(1, 200, false)
    modelPresets.value = data.data.items || []
  } catch { /* ignore */ }
}

async function loadSuites() {
  try {
    const { data } = await listEnabledBenchmarkSuites()
    suites.value = data.data.items || []
  } catch {
    toast.error(t('benchmark.loadSuitesFailed'))
  }
}

// 单次轮询：刷新全局指标 + 当前页进行中任务；有任务终结则重载当前页
async function tick() {
  await Promise.all([loadStats(), pollActive()])
}

async function pollActive() {
  const active = activeTasks.value
  if (!active.length) return
  let anySettled = false
  for (const t of active) {
    try {
      const { data } = await getBenchmark(t.id)
      Object.assign(t, data.data)
      if (t.status === 'success' || t.status === 'failed' || t.status === 'stopped') anySettled = true
    } catch { /* silent */ }
  }
  if (anySettled) loadTasks()
}

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
  if (!selectedSuite.value?.needs_judge) form.judgeModelId = null
  form.suiteConfig = {}
}

function onLimitPresetChange(v: string | number | null) {
  if (v === 'custom') form.executionConfig.limit = form.executionConfig.limit ?? 100
  else if (v === 'full') form.executionConfig.limit = null
  else form.executionConfig.limit = Number(v)
}

async function onSubmit() {
  if (!form.suiteKey) return toast.warning(t('benchmark.selectSuiteWarn'))
  if (!form.targetModelId) return toast.warning(t('benchmark.selectTargetWarn'))
  const needsJudge = selectedSuite.value?.needs_judge
  if (needsJudge && !form.judgeModelId) return toast.warning(t('benchmark.needJudgeWarn'))

  const taskName = form.taskName.trim() || autoTaskName()
  submitting.value = true
  try {
    await submitBenchmark({
      task_name: taskName,
      notes: form.notes.trim() || null,
      benchmark_suite: form.suiteKey,
      target_model_id: form.targetModelId,
      judge_model_id: needsJudge ? form.judgeModelId : null,
      execution_config: form.executionConfig,
      suite_config: form.suiteConfig,
    })
    toast.success(t('benchmark.submitSuccess'))
    showDialog.value = false
    await Promise.all([loadTasks(), loadStats()])
  } catch (err: unknown) {
    toast.error(errMsg(err) || t('benchmark.submitFailed'))
  } finally {
    submitting.value = false
  }
}

function autoTaskName(): string {
  const model = modelPresets.value.find((m) => m.id === form.targetModelId)
  const modelName = model?.display_name || 'model'
  const suiteName = selectedSuite.value?.display_name || form.suiteKey
  const now = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  const ts = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}`
  return `${modelName}-${suiteName}-${ts}`.slice(0, 100)
}

async function onRetry(id: number) {
  try {
    await retryBenchmark(id)
    toast.success(t('benchmark.retrySuccess'))
    await Promise.all([loadTasks(), loadStats()])
  } catch (err: unknown) {
    toast.error(errMsg(err) || t('benchmark.retryFailed'))
  }
}

async function onStop(id: number) {
  try {
    await stopBenchmark(id)
    toast.success(t('benchmark.stopSuccess'))
    await Promise.all([loadTasks(), loadStats()])
  } catch (err: unknown) {
    toast.error(errMsg(err) || t('benchmark.stopFailed'))
  }
}

async function onDelete(id: number) {
  const ok = await confirm({ message: t('benchmark.deleteConfirm'), tone: 'danger' })
  if (!ok) return
  try {
    await deleteBenchmark(id)
    expandedKeys.value = expandedKeys.value.filter((k) => k !== id)
    toast.success(t('common.deleteSuccess'))
    await Promise.all([loadTasks(), loadStats()])
  } catch (err: unknown) {
    toast.error(errMsg(err) || t('benchmark.deleteFailed'))
  }
}

// 手风琴：同一时间最多展开一个任务；展开新行时自动收起旧行
function onExpand(keys: (string | number)[]) {
  const old = expandedKeys.value
  if (keys.length > old.length) {
    const newly = keys.find((k) => !old.includes(k))
    expandedKeys.value = newly !== undefined ? [newly] : []
  } else {
    expandedKeys.value = keys
  }
}

function onPageChange(p: number) {
  page.value = p
  expandedKeys.value = []   // 换页清空展开状态
  loadTasks()
}

function openLog(id: number) {
  logTaskId.value = id
  logDialogVisible.value = true
}

function suiteLabel(key: string) {
  return suites.value.find((x) => x.key === key)?.display_name ?? key
}
function modelLabel(m?: ModelConfig | null) {
  return m ? (m.display_name || m.model_name || '—') : '—'
}
function primaryMetric(row: BenchmarkTask) {
  const metrics = row.result?.metrics
  if (!metrics || !Object.keys(metrics).length) return null
  const key = 'accuracy' in metrics ? 'accuracy' : Object.keys(metrics)[0]
  const v = metrics[key]
  const val = typeof v === 'number' ? (Number.isInteger(v) ? v : v.toFixed(4)) : v
  return `${key}: ${val}`
}
function fmtTime(t?: string | null) {
  return t ? new Date(t).toLocaleString() : '—'
}
function errMsg(err: unknown): string | undefined {
  return (err as { response?: { data?: { message?: string } } })?.response?.data?.message
}
</script>
