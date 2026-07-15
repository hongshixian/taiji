<template>
  <div class="page-shell page-shell--wide">
    <header class="mb-8 flex flex-col gap-2">
      <span class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">任务 · 自动红队测评</span>
      <div class="flex items-center justify-between gap-6">
        <h1 class="m-0 text-3xl font-bold tracking-tight text-fg">自动红队测评</h1>
        <UiButton @click="showDialog = true"><Plus class="size-4" /> 新建测评</UiButton>
      </div>
      <p class="m-0 max-w-[64ch] text-sm text-fg-secondary">
        选择红队攻击方法对目标模型发起自动化对抗测试，评估模型安全边界。
      </p>
    </header>

    <section class="mb-8 grid grid-cols-[repeat(auto-fit,minmax(180px,1fr))] gap-5">
      <div class="flex flex-col gap-2 rounded-lg border border-line bg-surface-sunken p-6">
        <span class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">进行中</span>
        <span class="font-mono text-3xl font-bold text-fg">{{ activeTasks.length }}</span>
      </div>
      <div class="flex flex-col gap-2 rounded-lg border border-line bg-surface-sunken p-6">
        <span class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">历史记录</span>
        <span class="font-mono text-3xl font-bold text-fg">{{ total }}</span>
      </div>
      <div class="flex flex-col gap-2 rounded-lg border border-line bg-surface-sunken p-6">
        <span class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">轮询间隔</span>
        <span class="font-mono text-3xl font-bold text-fg">2 秒</span>
      </div>
    </section>

    <!-- 新建对话框 -->
    <UiDialog v-model="showDialog" title="新建自动红队测评" width="600px" @update:model-value="!$event && closeDialog()">
      <div class="flex flex-col gap-4">
        <UiFormItem label="任务名称" required inline>
          <UiInput v-model="form.taskName" placeholder="例：GPT-4o 安全边界测试" :maxlength="100" />
        </UiFormItem>
        <UiFormItem label="被测模型" required inline>
          <UiSelect v-model="selectedModelId" :options="modelOptions" placeholder="选择已配置的模型" filterable clearable @update:model-value="applyModelPreset" />
        </UiFormItem>
        <UiFormItem label="红队方法" required inline>
          <UiSelect v-model="form.attackMethod" :options="methodOptions" placeholder="选择红队攻击方法" />
        </UiFormItem>
      </div>
      <template #footer>
        <UiButton variant="secondary" @click="closeDialog">取消</UiButton>
        <UiButton :loading="submitting" @click="handleSubmit">提交测评</UiButton>
      </template>
    </UiDialog>

    <!-- 进行中 -->
    <section v-if="activeTasks.length" class="mb-8">
      <h2 class="mb-5 text-lg font-semibold text-fg">进行中</h2>
      <div class="flex flex-col gap-5">
        <article v-for="task in activeTasks" :key="'a-' + task.id" class="flex flex-col gap-5 rounded-lg border border-line bg-surface p-6 shadow-xs">
          <header class="flex items-start justify-between gap-5">
            <div class="flex min-w-0 flex-1 flex-col gap-1">
              <span class="truncate font-semibold text-fg">{{ task.task_name || '提交中…' }}</span>
              <span v-if="task.target_model_name" class="font-mono text-xs text-fg-tertiary">{{ task.target_model_name }}</span>
            </div>
            <div class="flex shrink-0 items-center gap-4">
              <StatusPill :tone="statusTone(task.frontendStatus)" :label="statusLabel(task.frontendStatus)" dot />
              <UiButton v-if="canOpenTaskLogs(task)" variant="text" size="sm" @click="openTaskLogs(task)">日志</UiButton>
            </div>
          </header>
          <UiProgress :percentage="100" indeterminate :stroke-width="6" :show-text="false" />
          <footer class="flex items-baseline gap-3 text-fg-secondary">
            <span class="text-xs text-fg-tertiary">已等待</span>
            <span class="font-mono text-sm">{{ formatElapsed(task.elapsed) }}</span>
            <span class="text-xs text-fg-tertiary">·</span>
            <span class="text-xs text-fg-tertiary">后台执行中，完成后自动刷新</span>
          </footer>
        </article>
      </div>
    </section>

    <!-- 历史 -->
    <section v-if="historyTasks.length" class="rounded-lg border border-line bg-surface p-6">
      <div class="mb-6 flex items-center justify-between">
        <h2 class="text-lg font-semibold text-fg">历史记录</h2>
        <span class="text-xs text-fg-tertiary">第 {{ page }} 页 · 每页 {{ perPage }} 条</span>
      </div>
      <UiTable :columns="columns" :data="historyTasks" row-key="id" expandable :expanded-keys="expandedKeys" :loading="tableLoading" stripe @update:expanded-keys="expandedKeys = $event">
        <template #cell-attack_method="{ row }"><UiBadge tone="brand">{{ methodName(row.attack_method) }}</UiBadge></template>
        <template #cell-status="{ row }"><StatusPill :tone="dbStatusTone(row.status)" :label="dbStatusLabel(row.status)" /></template>
        <template #cell-created_at="{ row }"><span class="font-mono text-xs">{{ formatTime(row.created_at) }}</span></template>
        <template #cell-actions="{ row }">
          <div class="flex items-center gap-1">
            <UiButton variant="text" size="sm" @click="openTaskLogs(row)">日志</UiButton>
            <UiButton v-if="row.status === 'failed'" variant="text" size="sm" @click="retryDbTask(row)">重试</UiButton>
            <UiButton v-if="has('task:delete:any')" variant="danger-text" size="sm" @click="handleDelete(row)">删除</UiButton>
          </div>
        </template>
        <template #expand="{ row }">
          <div class="grid grid-cols-[repeat(auto-fill,minmax(260px,1fr))] gap-6">
            <div class="flex flex-col gap-3 rounded-lg border border-line bg-surface-sunken p-6">
              <p class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">任务信息</p>
              <dl class="grid grid-cols-[auto_1fr] items-baseline gap-x-6 gap-y-3 text-sm">
                <dt class="text-xs text-fg-secondary">ID</dt><dd class="m-0 font-mono">{{ row.id }}</dd>
                <dt class="text-xs text-fg-secondary">状态</dt><dd class="m-0"><StatusPill :tone="dbStatusTone(row.status)" :label="dbStatusLabel(row.status)" /></dd>
                <dt class="text-xs text-fg-secondary">创建</dt><dd class="m-0 font-mono">{{ formatTime(row.created_at) }}</dd>
                <dt class="text-xs text-fg-secondary">完成</dt><dd class="m-0 font-mono">{{ formatTime(row.completed_at) || '—' }}</dd>
                <template v-if="row.error_message"><dt class="text-xs text-fg-secondary">错误</dt><dd class="m-0 text-danger">{{ row.error_message }}</dd></template>
              </dl>
            </div>
            <div class="flex flex-col gap-3 rounded-lg border border-line bg-surface-sunken p-6">
              <p class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">攻击配置</p>
              <dl class="grid grid-cols-[auto_1fr] items-baseline gap-x-6 gap-y-3 text-sm">
                <dt class="text-xs text-fg-secondary">方法</dt><dd class="m-0"><UiBadge tone="brand">{{ methodName(row.attack_method) }}</UiBadge></dd>
              </dl>
              <pre v-if="row.attack_config" class="m-0 overflow-x-auto rounded-sm border border-line bg-canvas p-4 font-mono text-xs text-fg-secondary">{{ JSON.stringify(row.attack_config, null, 2) }}</pre>
              <span v-else class="text-xs text-fg-tertiary">使用默认配置</span>
            </div>
            <div class="col-span-full flex flex-col gap-3 rounded-lg border border-line bg-surface-sunken p-6">
              <p class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">测评结果</p>
              <pre v-if="row.result" class="m-0 overflow-x-auto rounded-sm border border-line bg-canvas p-4 font-mono text-xs text-fg-secondary">{{ JSON.stringify(row.result, null, 2) }}</pre>
              <div v-else class="flex flex-col items-center gap-2 py-8 text-fg-tertiary">
                <TriangleAlert class="size-8" />
                <p class="text-xs">暂无结果</p>
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
      description="还没有提交过红队测评"
    >
      <UiButton @click="showDialog = true"><Plus class="size-4" /> 提交第一个测评</UiButton>
    </UiEmpty>

    <TaskLogDialog v-model:visible="logVisible" :task-id="logTaskId" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, computed } from 'vue'
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
const logVisible = ref(false)
const logTaskId = ref<number | null>(null)
const modelPresets = ref<ModelConfig[]>([])
const selectedModelId = ref<number | null>(null)
const expandedKeys = ref<(string | number)[]>([])

const METHOD_LABELS: Record<string, string> = {
  gcg: 'GCG', gcg_ensemble: 'GCG Ensemble', gptfuzz: 'GPTFuzz', pair: 'PAIR',
  tap: 'TAP', autodan: 'AutoDAN', autoprompt: 'AutoPrompt',
}
const methodOptions: SelectOption[] = [
  { label: 'GCG（贪婪坐标梯度攻击）', value: 'gcg' },
  { label: 'GCG Ensemble（集成梯度攻击）', value: 'gcg_ensemble' },
  { label: 'GPTFuzz（模糊测试攻击）', value: 'gptfuzz' },
  { label: 'PAIR（提示自动迭代精炼）', value: 'pair' },
  { label: 'TAP（树状攻击与剪枝）', value: 'tap' },
  { label: 'AutoDAN（自动化 DAN 攻击）', value: 'autodan' },
  { label: 'AutoPrompt（自动提示搜索）', value: 'autoprompt' },
]

const columns: TableColumn[] = [
  { key: 'task_name', label: '任务名称', minWidth: 170, tooltip: true },
  { key: 'target_model_name', label: '目标模型', minWidth: 140, tooltip: true },
  { key: 'attack_method', label: '红队方法', width: 140 },
  { key: 'status', label: '状态', width: 100 },
  { key: 'created_at', label: '创建时间', width: 160 },
  { key: 'actions', label: '操作', width: 180, fixed: 'right' },
]

const modelOptions = computed<SelectOption[]>(() =>
  modelPresets.value.map((m) => ({ label: m.display_name, value: m.id, badge: m.model_name })),
)

const form = reactive({ taskName: '', targetModelName: '', attackMethod: '' })

function methodName(key: string) { return METHOD_LABELS[key] || key }

const FS_LABEL: Record<string, string> = { submitting: '提交中', submit_failed: '提交失败', pending: '排队中', running: '测评中', success: '已完成', failed: '失败', timeout: '超时', not_found: '任务丢失', query_error: '查询异常' }
const FS_TONE: Record<string, string> = { submitting: 'info', submit_failed: 'danger', pending: 'neutral', running: 'info', success: 'success', failed: 'danger', timeout: 'warning', not_found: 'warning', query_error: 'neutral' }
function statusLabel(s: string) { return FS_LABEL[s] || s }
function statusTone(s: string) { return (FS_TONE[s] || 'neutral') as 'info' | 'success' | 'danger' | 'warning' | 'neutral' }
const DB_LABEL: Record<string, string> = { pending: '排队中', running: '测评中', success: '已完成', failed: '失败' }
const DB_TONE: Record<string, string> = { pending: 'neutral', running: 'info', success: 'success', failed: 'danger' }
function dbStatusLabel(s: string) { return DB_LABEL[s] || s }
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
    toast.success('已重新提交')
  } catch (err: unknown) {
    toast.error('重试失败：' + (errMsg(err) || '网络异常'))
  }
}

async function handleDelete(row: HistoryTask) {
  const ok = await confirm({ message: '确定删除该测评任务？删除后不可恢复。', title: '删除确认', tone: 'danger', confirmText: '确认删除' })
  if (!ok) return
  try {
    await deleteRedTeam(row.id)
    historyTasks.value = historyTasks.value.filter((t) => t.id !== row.id)
    total.value--
    toast.success('任务已删除')
  } catch (err: unknown) {
    toast.error('删除失败：' + (errMsg(err) || '网络异常'))
  }
}

function _updateActiveTask(taskId: number, updates: Partial<ActiveTask>) {
  const t = activeTasks.value.find((x) => x.id === taskId)
  if (t) Object.assign(t, updates)
}
function _getActiveTask(taskId: number) { return activeTasks.value.find((t) => t.id === taskId) }

async function handleSubmit() {
  if (!form.taskName.trim()) return toast.warning('请填写任务名称')
  if (!form.targetModelName.trim()) return toast.warning('请从模型库选择被测模型')
  if (!form.attackMethod) return toast.warning('请选择红队方法')

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
    toast.success('红队测评任务已提交')
  } catch (err: unknown) {
    _updateActiveTask(tempId, { frontendStatus: 'submit_failed', error: errMsg(err) || '提交失败' })
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
    const t = _getActiveTask(taskId)
    if (!t) { stopPolling(taskId); return }
    _updateActiveTask(taskId, { pollCount: t.pollCount + 1 })
    try {
      const { data } = await getRedTeam(t.id)
      const s = data.data.status
      if (s === 'success' || s === 'failed') {
        stopPolling(taskId)
        activeTasks.value = activeTasks.value.filter((x) => x.id !== taskId)
        historyTasks.value.unshift(data.data)
        total.value++
        if (s === 'success') toast.success('红队测评完成')
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
