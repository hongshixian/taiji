<template>
  <div class="page-shell page-shell--wide">
    <header class="mb-8 flex flex-col gap-2">
      <span class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">{{ t('redteam.pageEyebrow') }}</span>
      <div class="flex items-center justify-between gap-6">
        <h1 class="m-0 text-3xl font-bold tracking-tight text-fg">{{ t('redteam.pageTitle') }}</h1>
        <UiButton @click="showDialog = true"><Plus class="size-4" /> {{ t('redteam.newTask') }}</UiButton>
      </div>
      <p class="m-0 max-w-[64ch] text-sm text-fg-secondary">
        {{ t('redteam.pageDesc') }}
      </p>
    </header>

    <section class="mb-8 grid grid-cols-[repeat(auto-fit,minmax(180px,1fr))] gap-5">
      <div class="flex flex-col gap-2 rounded-lg border border-line bg-surface-sunken p-6">
        <span class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">{{ t('redteam.inProgress') }}</span>
        <span class="font-mono text-3xl font-bold text-fg">{{ activeTasks.length }}</span>
      </div>
      <div class="flex flex-col gap-2 rounded-lg border border-line bg-surface-sunken p-6">
        <span class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">{{ t('redteam.history') }}</span>
        <span class="font-mono text-3xl font-bold text-fg">{{ total }}</span>
      </div>
      <div class="flex flex-col gap-2 rounded-lg border border-line bg-surface-sunken p-6">
        <span class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">{{ t('redteam.pollInterval') }}</span>
        <span class="font-mono text-3xl font-bold text-fg">{{ t('redteam.pollIntervalValue') }}</span>
      </div>
    </section>

    <!-- 新建对话框 -->
    <UiDialog v-model="showDialog" :title="t('redteam.dialogTitle')" width="600px" @update:model-value="!$event && closeDialog()">
      <div class="flex flex-col gap-4">
        <UiFormItem :label="t('redteam.taskName')" required inline>
          <UiInput v-model="form.taskName" :placeholder="t('redteam.taskNamePlaceholder')" :maxlength="100" />
        </UiFormItem>
        <UiFormItem :label="t('redteam.targetModel')" required inline>
          <UiSelect v-model="selectedModelId" :options="modelOptions" :placeholder="t('redteam.targetModelPlaceholder')" filterable clearable @update:model-value="applyModelPreset" />
        </UiFormItem>
        <UiFormItem :label="t('redteam.attackMethod')" required inline>
          <UiSelect v-model="form.attackMethod" :options="methodOptions" :placeholder="t('redteam.attackMethodPlaceholder')" />
        </UiFormItem>
      </div>
      <template #footer>
        <UiButton variant="secondary" @click="closeDialog">{{ t('common.cancel') }}</UiButton>
        <UiButton :loading="submitting" @click="handleSubmit">{{ t('redteam.submitTask') }}</UiButton>
      </template>
    </UiDialog>

    <!-- 进行中 -->
    <section v-if="activeTasks.length" class="mb-8">
      <h2 class="mb-5 text-lg font-semibold text-fg">{{ t('redteam.inProgress') }}</h2>
      <div class="flex flex-col gap-5">
        <article v-for="task in activeTasks" :key="'a-' + task.id" class="flex flex-col gap-5 rounded-lg border border-line bg-surface p-6 shadow-xs">
          <header class="flex items-start justify-between gap-5">
            <div class="flex min-w-0 flex-1 flex-col gap-1">
              <span class="truncate font-semibold text-fg">{{ task.task_name || t('redteam.submittingPlaceholder') }}</span>
              <span v-if="task.target_model_name" class="font-mono text-xs text-fg-tertiary">{{ task.target_model_name }}</span>
            </div>
            <div class="flex shrink-0 items-center gap-4">
              <StatusPill :tone="statusTone(task.frontendStatus)" :label="statusLabel(task.frontendStatus)" dot />
              <UiButton v-if="canOpenTaskLogs(task)" variant="text" size="sm" @click="openTaskLogs(task)">{{ t('redteam.log') }}</UiButton>
            </div>
          </header>
          <UiProgress :percentage="100" indeterminate :stroke-width="6" :show-text="false" />
          <footer class="flex items-baseline gap-3 text-fg-secondary">
            <span class="text-xs text-fg-tertiary">{{ t('redteam.waited') }}</span>
            <span class="font-mono text-sm">{{ formatElapsed(task.elapsed) }}</span>
            <span class="text-xs text-fg-tertiary">·</span>
            <span class="text-xs text-fg-tertiary">{{ t('redteam.runningHint') }}</span>
          </footer>
        </article>
      </div>
    </section>

    <!-- 历史 -->
    <section v-if="historyTasks.length" class="rounded-lg border border-line bg-surface p-6">
      <div class="mb-6 flex items-center justify-between">
        <h2 class="text-lg font-semibold text-fg">{{ t('redteam.history') }}</h2>
        <span class="text-xs text-fg-tertiary">{{ t('common.page', { page }) }} · {{ t('common.perPage', { n: perPage }) }}</span>
      </div>
      <UiTable :columns="columns" :data="historyTasks" row-key="id" expandable :expanded-keys="expandedKeys" :loading="tableLoading" stripe @update:expanded-keys="expandedKeys = $event">
        <template #cell-attack_method="{ row }"><UiBadge tone="brand">{{ methodName(row.attack_method) }}</UiBadge></template>
        <template #cell-status="{ row }"><StatusPill :tone="dbStatusTone(row.status)" :label="dbStatusLabel(row.status)" /></template>
        <template #cell-created_at="{ row }"><span class="font-mono text-xs">{{ formatTime(row.created_at) }}</span></template>
        <template #cell-actions="{ row }">
          <div class="flex items-center gap-1">
            <UiButton variant="text" size="sm" @click="openTaskLogs(row)">{{ t('redteam.log') }}</UiButton>
            <UiButton v-if="row.status === 'failed'" variant="text" size="sm" @click="retryDbTask(row)">{{ t('common.retry') }}</UiButton>
            <UiButton v-if="has('task:delete:any')" variant="danger-text" size="sm" @click="handleDelete(row)">{{ t('common.delete') }}</UiButton>
          </div>
        </template>
        <template #expand="{ row }">
          <div class="grid grid-cols-[repeat(auto-fill,minmax(260px,1fr))] gap-6">
            <div class="flex flex-col gap-3 rounded-lg border border-line bg-surface-sunken p-6">
              <p class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">{{ t('redteam.infoTitle') }}</p>
              <dl class="grid grid-cols-[auto_1fr] items-baseline gap-x-6 gap-y-3 text-sm">
                <dt class="text-xs text-fg-secondary">ID</dt><dd class="m-0 font-mono">{{ row.id }}</dd>
                <dt class="text-xs text-fg-secondary">{{ t('common.status') }}</dt><dd class="m-0"><StatusPill :tone="dbStatusTone(row.status)" :label="dbStatusLabel(row.status)" /></dd>
                <dt class="text-xs text-fg-secondary">{{ t('redteam.infoCreated') }}</dt><dd class="m-0 font-mono">{{ formatTime(row.created_at) }}</dd>
                <dt class="text-xs text-fg-secondary">{{ t('redteam.infoCompleted') }}</dt><dd class="m-0 font-mono">{{ formatTime(row.completed_at) || '—' }}</dd>
                <template v-if="row.error_message"><dt class="text-xs text-fg-secondary">{{ t('redteam.infoError') }}</dt><dd class="m-0 text-danger">{{ row.error_message }}</dd></template>
              </dl>
            </div>
            <div class="flex flex-col gap-3 rounded-lg border border-line bg-surface-sunken p-6">
              <p class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">{{ t('redteam.attackConfigTitle') }}</p>
              <dl class="grid grid-cols-[auto_1fr] items-baseline gap-x-6 gap-y-3 text-sm">
                <dt class="text-xs text-fg-secondary">{{ t('redteam.method') }}</dt><dd class="m-0"><UiBadge tone="brand">{{ methodName(row.attack_method) }}</UiBadge></dd>
              </dl>
              <pre v-if="row.attack_config" class="m-0 overflow-x-auto rounded-sm border border-line bg-canvas p-4 font-mono text-xs text-fg-secondary">{{ JSON.stringify(row.attack_config, null, 2) }}</pre>
              <span v-else class="text-xs text-fg-tertiary">{{ t('redteam.defaultConfig') }}</span>
            </div>
            <div class="col-span-full flex flex-col gap-3 rounded-lg border border-line bg-surface-sunken p-6">
              <p class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">{{ t('redteam.resultTitle') }}</p>
              <pre v-if="row.result" class="m-0 overflow-x-auto rounded-sm border border-line bg-canvas p-4 font-mono text-xs text-fg-secondary">{{ JSON.stringify(row.result, null, 2) }}</pre>
              <div v-else class="flex flex-col items-center gap-2 py-8 text-fg-tertiary">
                <TriangleAlert class="size-8" />
                <p class="text-xs">{{ t('redteam.noResult') }}</p>
              </div>
            </div>
          </div>
        </template>
      </UiTable>
      <div v-if="total > perPage" class="mt-6 flex justify-end">
        <UiPagination :current-page="page" :page-size="perPage" :total="total" @current-change="onPageChange" />
      </div>
    </section>

    <UiEmpty
      v-if="!activeTasks.length && !historyTasks.length && !tableLoading"
      :description="t('redteam.emptyDesc')"
    >
      <UiButton @click="showDialog = true"><Plus class="size-4" /> {{ t('redteam.submitFirst') }}</UiButton>
    </UiEmpty>

    <TaskLogDialog v-model:visible="logVisible" :task-id="logTaskId" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Plus, TriangleAlert } from 'lucide-vue-next'
import { toast } from '@/lib/toast'
import { confirm } from '@/lib/confirm'
import { deleteRedTeam, getRedTeam, listRedTeams, retryRedTeam, submitRedTeam } from '@/api/redTeam'
import { listModels } from '@/api/model'
import type { ModelConfig } from '@/api/types'
import TaskLogDialog from '@/components/TaskLogDialog.vue'
import StatusPill from '@/components/StatusPill.vue'
import UiButton from '@/components/ui/Button.vue'
import UiInput from '@/components/ui/Input.vue'
import UiSelect, { type SelectOption } from '@/components/ui/Select.vue'
import UiDialog from '@/components/ui/Dialog.vue'
import UiFormItem from '@/components/ui/FormItem.vue'
import UiBadge from '@/components/ui/Badge.vue'
import UiProgress from '@/components/ui/Progress.vue'
import UiEmpty from '@/components/ui/Empty.vue'
import UiTable, { type TableColumn } from '@/components/ui/Table.vue'
import UiPagination from '@/components/ui/Pagination.vue'
import { usePermission } from '@/composables/usePermission'

interface ActiveTask {
  id: number
  task_name: string
  target_model_name?: string
  frontendStatus: string
  pollCount: number
  pollTimer: ReturnType<typeof setInterval> | null
  elapsed: number
  elapsedTimer: ReturnType<typeof setInterval> | null
  error?: string
  [k: string]: unknown
}
type HistoryTask = Record<string, unknown> & { id: number; status: string }

const showDialog = ref(false)
const submitting = ref(false)
const activeTasks = ref<ActiveTask[]>([])
const historyTasks = ref<HistoryTask[]>([])
const tableLoading = ref(false)
const page = ref(1)
const perPage = 20
const total = ref(0)
const { has } = usePermission()
const { t } = useI18n()
const logVisible = ref(false)
const logTaskId = ref<number | null>(null)
const modelPresets = ref<ModelConfig[]>([])
const selectedModelId = ref<number | null>(null)
const expandedKeys = ref<(string | number)[]>([])

const METHOD_LABELS: Record<string, string> = {
  gcg: 'GCG', gcg_ensemble: 'GCG Ensemble', gptfuzz: 'GPTFuzz', pair: 'PAIR',
  tap: 'TAP', autodan: 'AutoDAN', autoprompt: 'AutoPrompt',
}
const methodOptions = computed<SelectOption[]>(() => [
  { label: t('redteam.methodGcg'), value: 'gcg' },
  { label: t('redteam.methodGcgEnsemble'), value: 'gcg_ensemble' },
  { label: t('redteam.methodGptfuzz'), value: 'gptfuzz' },
  { label: t('redteam.methodPair'), value: 'pair' },
  { label: t('redteam.methodTap'), value: 'tap' },
  { label: t('redteam.methodAutodan'), value: 'autodan' },
  { label: t('redteam.methodAutoprompt'), value: 'autoprompt' },
])

const columns = computed<TableColumn[]>(() => [
  { key: 'task_name', label: t('redteam.colTaskName'), minWidth: 170, tooltip: true },
  { key: 'target_model_name', label: t('redteam.colTargetModel'), minWidth: 140, tooltip: true },
  { key: 'attack_method', label: t('redteam.colAttackMethod'), width: 140 },
  { key: 'status', label: t('common.status'), width: 100 },
  { key: 'created_at', label: t('common.createdAt'), width: 160 },
  { key: 'actions', label: t('common.actions'), width: 180, fixed: 'right' },
])

const modelOptions = computed<SelectOption[]>(() =>
  modelPresets.value.map((m) => ({ label: m.display_name, value: m.id, badge: m.model_name })),
)

const form = reactive({ taskName: '', targetModelName: '', attackMethod: '' })

function methodName(key: string) { return METHOD_LABELS[key] || key }

const FS_TONE: Record<string, string> = { submitting: 'info', submit_failed: 'danger', pending: 'neutral', running: 'info', success: 'success', failed: 'danger', timeout: 'warning', not_found: 'warning', query_error: 'neutral' }
function statusLabel(s: string) { return t(`taskStatus.${s}`) }
function statusTone(s: string) { return (FS_TONE[s] || 'neutral') as 'info' | 'success' | 'danger' | 'warning' | 'neutral' }
const DB_TONE: Record<string, string> = { pending: 'neutral', running: 'info', success: 'success', failed: 'danger' }
function dbStatusLabel(s: string) { return t(`taskStatus.${s}`) }
function dbStatusTone(s: string) { return (DB_TONE[s] || 'neutral') as 'info' | 'success' | 'danger' | 'warning' | 'neutral' }

function formatTime(iso?: string | null) { return iso ? new Date(iso).toLocaleString('zh-CN') : '' }
function formatElapsed(sec: number) {
  const s = sec || 0
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m ${s % 60}s`
  return `${Math.floor(m / 60)}h ${m % 60}m`
}
function openTaskLogs(row: { id: number }) { logTaskId.value = row.id; logVisible.value = true }
function canOpenTaskLogs(task: ActiveTask) { return !['submitting', 'submit_failed'].includes(task.frontendStatus) }

function closeDialog() {
  showDialog.value = false
  selectedModelId.value = null
  Object.assign(form, { taskName: '', targetModelName: '', attackMethod: '' })
}

async function fetchModelPresets() {
  try {
    const { data } = await listModels(1, 200, false)
    modelPresets.value = data.data.items
  } catch { /* non-critical */ }
}

function applyModelPreset(id: string | number | null) {
  const m = modelPresets.value.find((x) => x.id === id)
  if (m) form.targetModelName = m.model_name
}

async function fetchHistoryTasks() {
  tableLoading.value = true
  try {
    const { data } = await listRedTeams(page.value, perPage)
    historyTasks.value = data.data.items
    total.value = data.data.total
  } catch { /* ignore */ } finally {
    tableLoading.value = false
  }
}

function onPageChange(p: number) { page.value = p; fetchHistoryTasks() }

async function retryDbTask(row: HistoryTask) {
  try {
    const { data } = await retryRedTeam(row.id)
    historyTasks.value = historyTasks.value.filter((t) => t.id !== row.id)
    total.value--
    const newId = data.data.id
    activeTasks.value.unshift({ ...data.data, id: newId, task_name: String(row.task_name ?? ''), frontendStatus: 'pending', pollCount: 0, pollTimer: null, elapsed: 0, elapsedTimer: null })
    startPolling(newId)
    toast.success(t('redteam.retrySuccess'))
  } catch (err: unknown) {
    toast.error(t('redteam.retryFailed') + (errMsg(err) || t('common.networkError')))
  }
}

async function handleDelete(row: HistoryTask) {
  const ok = await confirm({ message: t('redteam.deleteConfirmMsg'), title: t('redteam.deleteConfirmTitle'), tone: 'danger', confirmText: t('redteam.deleteConfirmBtn') })
  if (!ok) return
  try {
    await deleteRedTeam(row.id)
    historyTasks.value = historyTasks.value.filter((t) => t.id !== row.id)
    total.value--
    toast.success(t('redteam.deleteSuccess'))
  } catch (err: unknown) {
    toast.error(t('redteam.deleteFailed') + (errMsg(err) || t('common.networkError')))
  }
}

function _updateActiveTask(taskId: number, updates: Partial<ActiveTask>) {
  const t = activeTasks.value.find((x) => x.id === taskId)
  if (t) Object.assign(t, updates)
}
function _getActiveTask(taskId: number) { return activeTasks.value.find((t) => t.id === taskId) }

async function handleSubmit() {
  if (!form.taskName.trim()) return toast.warning(t('redteam.taskNameRequired'))
  if (!form.targetModelName.trim()) return toast.warning(t('redteam.targetModelRequired'))
  if (!form.attackMethod) return toast.warning(t('redteam.attackMethodRequired'))

  const payload = {
    task_name: form.taskName.trim(),
    target_model_name: form.targetModelName.trim(),
    attack_method: form.attackMethod,
    attack_config: null,
  }
  closeDialog()
  const tempId = Date.now()
  activeTasks.value.unshift({ id: tempId, task_name: payload.task_name, target_model_name: payload.target_model_name, frontendStatus: 'submitting', pollCount: 0, pollTimer: null, elapsed: 0, elapsedTimer: null })
  submitting.value = true
  try {
    const { data } = await submitRedTeam(payload)
    _updateActiveTask(tempId, { id: data.data.id, ...data.data, frontendStatus: 'pending' })
    startPolling(data.data.id)
    toast.success(t('redteam.submitSuccess'))
  } catch (err: unknown) {
    _updateActiveTask(tempId, { frontendStatus: 'submit_failed', error: errMsg(err) || t('redteam.submitFailed') })
  } finally {
    submitting.value = false
  }
}

function startPolling(taskId: number) {
  stopPolling(taskId)
  _updateActiveTask(taskId, { pollCount: 0 })
  const task = _getActiveTask(taskId)
  if (!task) return

  task.elapsedTimer = setInterval(() => {
    const t = _getActiveTask(taskId)
    if (t) t.elapsed++
  }, 1000)

  task.pollTimer = setInterval(async () => {
    const at = _getActiveTask(taskId)
    if (!at) { stopPolling(taskId); return }
    _updateActiveTask(taskId, { pollCount: at.pollCount + 1 })
    try {
      const { data } = await getRedTeam(at.id)
      const s = data.data.status
      if (s === 'success' || s === 'failed') {
        stopPolling(taskId)
        activeTasks.value = activeTasks.value.filter((x) => x.id !== taskId)
        historyTasks.value.unshift(data.data)
        total.value++
        if (s === 'success') toast.success(t('redteam.evalComplete'))
      } else {
        _updateActiveTask(taskId, { frontendStatus: s })
      }
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status
      if (status === 404) { _updateActiveTask(taskId, { frontendStatus: 'not_found' }); stopPolling(taskId) }
      else _updateActiveTask(taskId, { frontendStatus: 'query_error' })
    }
  }, 2000)
}

function stopPolling(taskId: number) {
  const t = _getActiveTask(taskId)
  if (t) {
    if (t.pollTimer) clearInterval(t.pollTimer)
    if (t.elapsedTimer) clearInterval(t.elapsedTimer)
    t.pollTimer = null
    t.elapsedTimer = null
  }
}

function errMsg(err: unknown): string | undefined {
  return (err as { response?: { data?: { message?: string } } })?.response?.data?.message
}

onMounted(() => { fetchHistoryTasks(); fetchModelPresets() })
onUnmounted(() => activeTasks.value.forEach((t) => {
  if (t.pollTimer) clearInterval(t.pollTimer)
  if (t.elapsedTimer) clearInterval(t.elapsedTimer)
}))
</script>
