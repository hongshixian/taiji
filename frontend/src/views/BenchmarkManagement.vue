<template>
  <div class="page-shell page-shell--wide">
    <header class="mb-8 flex flex-col gap-2">
      <span class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">任务 · Benchmark 测评</span>
      <div class="flex items-center justify-between gap-6">
        <h1 class="m-0 text-3xl font-bold tracking-tight text-fg">Benchmark 测评</h1>
        <UiButton @click="openCreateDialog">
          <Plus class="size-4" /> 新建测评
        </UiButton>
      </div>
      <p class="m-0 max-w-[64ch] text-sm text-fg-secondary">
        选择被测模型与评测集，由 Worker 异步驱动 inspect_evals 引擎执行标准化 Benchmark 评测。
      </p>
    </header>

    <!-- 指标 -->
    <section class="mb-8 grid grid-cols-[repeat(auto-fit,minmax(180px,1fr))] gap-5">
      <div class="flex flex-col gap-2 rounded-lg border border-line bg-surface-sunken p-6">
        <span class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">进行中</span>
        <span class="font-mono text-3xl font-bold text-fg">{{ activeTasks.length }}</span>
      </div>
      <div class="flex flex-col gap-2 rounded-lg border border-line bg-surface-sunken p-6">
        <span class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">累计任务</span>
        <span class="font-mono text-3xl font-bold text-fg">{{ total }}</span>
      </div>
      <div class="flex flex-col gap-2 rounded-lg border border-line bg-surface-sunken p-6">
        <span class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">可用评测集</span>
        <span class="font-mono text-3xl font-bold text-fg">{{ enabledSuites.length }}</span>
      </div>
    </section>

    <!-- 新建对话框 -->
    <UiDialog v-model="showDialog" title="新建 Benchmark 测评" width="720px">
      <div class="flex flex-col gap-6">
        <section class="flex flex-col gap-4 border-b border-line pb-5">
          <div class="font-semibold text-fg">基本信息</div>
          <UiFormItem label="任务名称" inline>
            <UiInput v-model="form.taskName" placeholder="留空则自动生成：模型-评测集-时间" :maxlength="100" />
          </UiFormItem>
          <UiFormItem label="备注" inline>
            <UiTextarea v-model="form.notes" :rows="2" placeholder="记录本次评测的目的（可选）" :maxlength="500" />
          </UiFormItem>
        </section>

        <section class="flex flex-col gap-4 border-b border-line pb-5">
          <div class="font-semibold text-fg">评测集</div>
          <UiFormItem label="Benchmark" required inline>
            <UiSelect
              v-model="form.suiteKey"
              :groups="suiteSelectGroups"
              placeholder="请选择评测集"
              filterable
              @update:model-value="onSuiteChange"
            />
          </UiFormItem>
          <UiAlert v-if="selectedSuite?.notes" type="info" :title="selectedSuite.notes" />
        </section>

        <section class="flex flex-col gap-4 border-b border-line pb-5">
          <div class="font-semibold text-fg">被测模型</div>
          <UiFormItem label="模型" required inline>
            <UiSelect v-model="form.targetModelId" :options="modelOptions" placeholder="选择已配置的模型" filterable />
          </UiFormItem>
          <p class="flex items-center gap-2 text-xs text-fg-tertiary">
            <Info class="size-4" /> 生成参数（temperature / max_tokens 等）来自模型管理页面，本次评测使用其固定值。
          </p>
        </section>

        <section v-if="selectedSuite?.needs_judge" class="flex flex-col gap-4 border-b border-line pb-5">
          <div class="font-semibold text-fg">评委模型</div>
          <UiFormItem label="模型" required inline>
            <UiSelect v-model="form.judgeModelId" :options="modelOptions" placeholder="选择评委模型" filterable />
          </UiFormItem>
          <p class="flex items-center gap-2 text-xs text-fg-tertiary">
            <Info class="size-4" /> 该评测集需要一个模型作为评委来判断答案质量。
          </p>
        </section>

        <section class="flex flex-col gap-4 border-b border-line pb-5">
          <div class="font-semibold text-fg">执行控制</div>
          <UiFormItem label="样本数量" inline>
            <UiSegmented v-model="limitPreset" :options="limitPresetOptions" @update:model-value="onLimitPresetChange" />
          </UiFormItem>
          <UiFormItem v-if="limitPreset === 'custom'" label="自定义样本数" inline>
            <UiInputNumber v-model="form.executionConfig.limit" :min="1" :max="20000" />
          </UiFormItem>
          <UiCollapse title="高级 (并发 / 重复次数 / 超时)">
            <div class="grid grid-cols-[repeat(auto-fit,minmax(180px,1fr))] gap-4">
              <UiFormItem label="并发数"><UiInputNumber v-model="form.executionConfig.max_connections" :min="1" :max="100" block /></UiFormItem>
              <UiFormItem label="重复次数"><UiInputNumber v-model="form.executionConfig.epochs" :min="1" :max="10" block /></UiFormItem>
              <UiFormItem label="超时(分钟)"><UiInputNumber v-model="form.executionConfig.timeout_minutes" :min="5" :max="720" block /></UiFormItem>
            </div>
          </UiCollapse>
        </section>

        <section v-if="selectedSuite?.config_schema?.fields?.length" class="flex flex-col gap-4">
          <div class="font-semibold text-fg">Suite 特有参数</div>
          <DynamicField
            v-for="field in selectedSuite.config_schema.fields"
            :key="field.key"
            :field="field"
            v-model="form.suiteConfig[field.key]"
          />
        </section>
      </div>

      <template #footer>
        <UiButton variant="secondary" @click="showDialog = false">取消</UiButton>
        <UiButton :loading="submitting" @click="onSubmit">提交任务</UiButton>
      </template>
    </UiDialog>

    <!-- 进行中 -->
    <section v-if="activeTasks.length" class="mb-8">
      <h2 class="mb-5 text-lg font-semibold text-fg">进行中</h2>
      <div class="grid grid-cols-[repeat(auto-fill,minmax(300px,1fr))] gap-5">
        <div v-for="t in activeTasks" :key="t.id" class="flex flex-col gap-4 rounded-lg border border-line bg-surface p-6 shadow-xs">
          <div class="flex items-center justify-between gap-4">
            <span class="font-semibold text-fg">{{ t.task_name || '(未命名)' }}</span>
            <StatusPill :tone="statusTone(t.status)" :label="statusLabel(t.status)" dot />
          </div>
          <div class="flex gap-5 text-xs text-fg-tertiary">
            <span>{{ suiteLabel(t.benchmark_suite) }}</span>
            <span>{{ modelLabel(t.target_model) }}</span>
          </div>
          <UiProgress
            v-if="t.progress && t.progress.total"
            :percentage="Math.round((t.progress.completed / t.progress.total) * 100)"
            :stroke-width="8"
          />
          <div v-else class="text-xs text-fg-tertiary">
            {{ t.status === 'pending' ? '等待 Worker 拾取…' : '准备中…' }}
          </div>
        </div>
      </div>
    </section>

    <!-- 历史 -->
    <section class="rounded-lg border border-line bg-surface p-6">
      <div class="mb-6 flex items-center justify-between">
        <h2 class="text-lg font-semibold text-fg">历史记录</h2>
        <UiButton variant="secondary" size="sm" :loading="loading" @click="loadTasks">刷新</UiButton>
      </div>

      <UiEmpty v-if="!loading && !historyTasks.length" description="还没有已完成的评测任务">
        <UiButton @click="openCreateDialog">新建测评</UiButton>
      </UiEmpty>

      <template v-else>
        <UiTable
          :columns="columns"
          :data="historyTasks"
          row-key="id"
          expandable
          :expanded-keys="expandedKeys"
          :loading="loading"
          @update:expanded-keys="expandedKeys = $event"
        >
          <template #cell-benchmark_suite="{ row }">{{ suiteLabel(row.benchmark_suite) }}</template>
          <template #cell-target_model="{ row }">{{ modelLabel(row.target_model) }}</template>
          <template #cell-status="{ row }">
            <StatusPill :tone="statusTone(row.status)" :label="statusLabel(row.status)" />
          </template>
          <template #cell-metric="{ row }">
            <span v-if="primaryMetric(row)" class="font-mono">{{ primaryMetric(row) }}</span>
            <span v-else class="text-fg-tertiary">—</span>
          </template>
          <template #cell-created_at="{ row }">{{ fmtTime(row.created_at) }}</template>
          <template #cell-actions="{ row }">
            <div class="flex items-center gap-1">
              <UiButton variant="text" size="sm" @click="openLog(row.id)">日志</UiButton>
              <UiButton variant="text" size="sm" @click="onRetry(row.id)">重试</UiButton>
              <UiButton v-if="canDelete" variant="danger-text" size="sm" @click="onDelete(row.id)">删除</UiButton>
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
import { Plus, Info } from 'lucide-vue-next'
import { toast } from '@/lib/toast'
import { confirm } from '@/lib/confirm'
import {
  submitBenchmark,
  getBenchmark,
  listBenchmarks,
  retryBenchmark,
  deleteBenchmark,
  listBenchmarkSuites,
} from '@/api/benchmark'
import { listModels } from '@/api/model'
import type { BenchmarkTask, SuiteDescriptor, ModelConfig } from '@/api/types'
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

const limitPresetOptions = [
  { label: '快速冒烟 (20)', value: '20' },
  { label: '标准 (200)', value: '200' },
  { label: '完整', value: 'full' },
  { label: '自定义', value: 'custom' },
]

const columns: TableColumn[] = [
  { key: 'task_name', label: '任务', minWidth: 180, tooltip: true },
  { key: 'benchmark_suite', label: '评测集', minWidth: 160, tooltip: true },
  { key: 'target_model', label: '被测模型', minWidth: 130, tooltip: true },
  { key: 'status', label: '状态', width: 100 },
  { key: 'metric', label: '主指标', width: 130 },
  { key: 'created_at', label: '创建时间', width: 160 },
  { key: 'actions', label: '操作', width: 170, fixed: 'right' },
]

const enabledSuites = computed(() => suites.value.filter((s) => !s.disabled))
const selectedSuite = computed(() => suites.value.find((s) => s.key === form.suiteKey) || null)
const activeTasks = computed(() => tasks.value.filter((t) => t.status === 'pending' || t.status === 'running'))
const historyTasks = computed(() => tasks.value.filter((t) => t.status === 'success' || t.status === 'failed'))

const modelOptions = computed<SelectOption[]>(() =>
  modelPresets.value.map((m) => ({ label: m.display_name, value: m.id, badge: m.api_protocol })),
)

const suiteSelectGroups = computed<SelectGroupDef[]>(() => {
  const groups: Record<string, { label: string; options: SelectOption[] }> = {
    capability: { label: '能力评测', options: [] },
    safety: { label: '安全评测', options: [] },
    alignment: { label: '对齐/行为评测', options: [] },
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
  await Promise.all([loadTasks(), loadModels(), loadSuites()])
  pollTimer = setInterval(pollActive, 2000)
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
    toast.error(errMsg(err) || '加载任务失败')
  } finally {
    loading.value = false
  }
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
    const { data } = await listBenchmarkSuites()
    suites.value = data.data.items || []
  } catch {
    toast.error('加载评测集失败')
  }
}

async function pollActive() {
  const active = activeTasks.value
  if (!active.length) return
  let anySettled = false
  for (const t of active) {
    try {
      const { data } = await getBenchmark(t.id)
      Object.assign(t, data.data)
      if (t.status === 'success' || t.status === 'failed') anySettled = true
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
  if (!form.suiteKey) return toast.warning('请选择评测集')
  if (!form.targetModelId) return toast.warning('请选择被测模型')
  const needsJudge = selectedSuite.value?.needs_judge
  if (needsJudge && !form.judgeModelId) return toast.warning('该评测集需要评委模型')

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
    toast.success('任务已提交')
    showDialog.value = false
    await loadTasks()
  } catch (err: unknown) {
    toast.error(errMsg(err) || '提交失败')
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
    toast.success('已重新提交')
    loadTasks()
  } catch (err: unknown) {
    toast.error(errMsg(err) || '重试失败')
  }
}

async function onDelete(id: number) {
  const ok = await confirm({ message: '确认删除这条评测任务？', tone: 'danger' })
  if (!ok) return
  try {
    await deleteBenchmark(id)
    expandedKeys.value = expandedKeys.value.filter((k) => k !== id)
    toast.success('已删除')
    loadTasks()
  } catch (err: unknown) {
    toast.error(errMsg(err) || '删除失败')
  }
}

function onPageChange(p: number) {
  page.value = p
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
