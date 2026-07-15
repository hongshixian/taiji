<template>
  <div class="page-shell page-shell--wide flex flex-col gap-8">
    <header class="page-header">
      <span class="page-header__eyebrow t-eyebrow">资源 · 模型库</span>
      <div class="flex items-center justify-between gap-6">
        <h1 class="page-header__title">模型管理</h1>
        <UiButton v-if="has('model:write')" @click="openCreateDialog">
          <Plus class="size-4" />添加模型
        </UiButton>
      </div>
      <p class="page-header__lede">
        配置被测模型的 API 信息，供测评任务直接调用。数据归属当前租户，其他租户不可见。
      </p>
    </header>

    <section
      v-if="loading || models.length"
      class="flex flex-col gap-6 rounded-lg border border-line bg-surface p-6 shadow-xs"
    >
      <div class="flex items-center gap-4">
        <label class="flex cursor-pointer items-center gap-2">
          <UiSwitch v-model="showInactive" @update:model-value="handleFilterChange" />
          <span class="text-xs text-fg-tertiary">显示已停用</span>
        </label>
      </div>

      <UiTable :columns="columns" :data="models" row-key="id" stripe :loading="loading">
        <template #cell-display_name="{ row }">
          <span class="font-medium text-fg">{{ (row as ModelItem).display_name }}</span>
        </template>
        <template #cell-model_name="{ value }">
          <span class="t-mono">{{ value }}</span>
        </template>
        <template #cell-api_protocol="{ value }">
          <UiBadge tone="neutral" class="font-mono">{{ value }}</UiBadge>
        </template>
        <template #cell-api_base_url="{ value }">
          <span class="t-mono block break-all text-xs text-fg-secondary">{{ value }}</span>
        </template>
        <template #cell-is_active="{ value }">
          <UiBadge :tone="value ? 'success' : 'danger'">{{ value ? '启用' : '停用' }}</UiBadge>
        </template>
        <template #cell-created_at="{ value }">
          <span class="t-mono">{{ formatTime(value as string | null) }}</span>
        </template>
        <template #cell-actions="{ row }">
          <div class="flex items-center gap-1">
            <UiButton
              variant="text"
              size="sm"
              :loading="testingId === (row as ModelItem).id"
              @click="handleTest(row as ModelItem)"
            >测试</UiButton>
            <UiButton
              v-if="has('model:write')"
              variant="text"
              size="sm"
              @click="openEditDialog(row as ModelItem)"
            >编辑</UiButton>
            <UiDropdown v-if="has('model:write') || has('model:delete')">
              <template #trigger>
                <UiButton variant="text" size="sm">更多<ChevronDown class="size-4" /></UiButton>
              </template>
              <template #default="{ close }">
                <UiDropdownItem
                  v-if="has('model:write')"
                  @select="close(); toggleActive(row as ModelItem)"
                >{{ (row as ModelItem).is_active ? '停用' : '启用' }}</UiDropdownItem>
                <UiDropdownItem
                  v-if="has('model:delete')"
                  danger
                  @select="close(); handleDelete(row as ModelItem)"
                >删除</UiDropdownItem>
              </template>
            </UiDropdown>
          </div>
        </template>
      </UiTable>

      <div v-if="total > perPage" class="flex justify-center">
        <UiPagination
          :current-page="page"
          :page-size="perPage"
          :total="total"
          @current-change="onPageChange"
        />
      </div>
    </section>

    <!-- 空状态 -->
    <section
      v-if="!loading && models.length === 0"
      class="flex flex-col items-center gap-5 rounded-lg border border-dashed border-line-strong bg-surface px-9 py-16 text-center"
    >
      <span class="t-eyebrow">暂无模型</span>
      <h3 class="m-0 text-2xl text-fg">还没有配置任何模型</h3>
      <p class="m-0 max-w-[48ch] text-fg-secondary">
        在这里维护被测模型的 API 地址、密钥等信息，创建测评任务时可直接从模型库选择，无需重复填写。
      </p>
      <UiButton v-if="has('model:write')" class="mt-3" @click="openCreateDialog">
        <Plus class="size-4" />添加第一个模型
      </UiButton>
    </section>

    <!-- 新建 / 编辑对话框 -->
    <UiDialog
      v-model="dialogVisible"
      :title="editMode ? '编辑模型配置' : '添加模型'"
      width="560px"
    >
      <div class="flex flex-col gap-4">
        <UiFormItem label="显示名称" required hint="显示在测评榜单和任务列表中的名称">
          <UiInput v-model="form.display_name" placeholder="例：GPT-4o（OpenAI 官方）" :maxlength="100" />
        </UiFormItem>
        <UiFormItem label="模型标识" required hint="API 请求 body 中的 model 字段值">
          <UiInput v-model="form.model_name" class="font-mono" placeholder="例：gpt-4o" :maxlength="200" />
        </UiFormItem>
        <UiFormItem label="API 协议" required>
          <UiSelect v-model="form.api_protocol" :options="protocolOptions" />
        </UiFormItem>
        <UiFormItem label="API 地址" required>
          <UiInput
            v-model="form.api_base_url"
            class="font-mono"
            placeholder="https://api.openai.com/v1"
            :maxlength="500"
          />
        </UiFormItem>
        <UiFormItem label="API Key">
          <UiInput
            v-model="form.api_key"
            type="password"
            class="font-mono"
            :placeholder="editMode ? '留空则不修改原有密钥' : 'sk-...（可选，加密存储）'"
            :maxlength="500"
          />
        </UiFormItem>
        <UiFormItem label="描述">
          <UiTextarea v-model="form.description" :rows="2" placeholder="可选的备注说明" :maxlength="500" />
        </UiFormItem>

        <div class="my-2 flex items-center gap-3 text-xs font-semibold text-fg-tertiary">
          <span>生成参数</span><span class="h-px flex-1 bg-line" />
        </div>
        <p class="-mt-2 text-xs leading-relaxed text-fg-tertiary">
          评测时将统一使用这里配置的采样参数，保证同一模型的结果可比。留空则由引擎使用默认值。
        </p>
        <div class="grid grid-cols-1 gap-x-6 gap-y-4 sm:grid-cols-2">
          <UiFormItem label="Temperature">
            <UiInputNumber
              v-model="form.gen_temperature"
              :min="0" :max="2" :step="0.1" :precision="2"
              block placeholder="可选"
            />
          </UiFormItem>
          <UiFormItem label="Top-P">
            <UiInputNumber
              v-model="form.gen_top_p"
              :min="0" :max="1" :step="0.05" :precision="2"
              block placeholder="可选"
            />
          </UiFormItem>
          <UiFormItem label="Max Tokens">
            <UiInputNumber
              v-model="form.gen_max_tokens"
              :min="1" :max="200000" :step="256"
              block placeholder="可选"
            />
          </UiFormItem>
          <UiFormItem label="Stop 序列">
            <UiInput v-model="form.gen_stop_sequences" placeholder="逗号分隔，可选" />
          </UiFormItem>
        </div>

        <UiFormItem v-if="editMode" label="状态">
          <label class="flex items-center gap-2">
            <UiSwitch v-model="form.is_active" />
            <span class="text-sm text-fg-secondary">{{ form.is_active ? '启用' : '停用' }}</span>
          </label>
        </UiFormItem>
      </div>
      <template #footer>
        <UiButton variant="secondary" @click="dialogVisible = false">取消</UiButton>
        <UiButton :loading="submitting" @click="handleSubmit">
          {{ editMode ? '保存' : '添加' }}
        </UiButton>
      </template>
    </UiDialog>

    <!-- 测试结果对话框 -->
    <UiDialog v-model="testDialogVisible" title="模型连通性测试" width="600px">
      <!-- 测试进行中 -->
      <div v-if="testing" class="flex min-h-[140px] flex-col items-center justify-center gap-4">
        <UiSpinner :size="28" />
        <span class="text-xs text-fg-tertiary">正在向模型发送测试请求…</span>
        <span class="text-xs text-fg-tertiary">模型：{{ testTargetName }}</span>
      </div>

      <!-- 测试结果 -->
      <div v-else-if="testResult" class="flex flex-col gap-5">
        <div class="flex items-center gap-4">
          <UiBadge :tone="testResult.ok ? 'success' : 'danger'">
            {{ testResult.ok ? '通过' : '失败' }}
          </UiBadge>
          <span class="text-xs text-fg-tertiary">模型：{{ testTargetName }}</span>
        </div>
        <div class="grid grid-cols-[repeat(auto-fit,minmax(150px,1fr))] gap-4 rounded-md border border-line bg-canvas p-4">
          <div class="flex flex-col gap-1">
            <span class="t-eyebrow">耗时</span>
            <span class="t-mono">{{ testResult.latency_ms }} ms</span>
          </div>
          <div class="flex flex-col gap-1">
            <span class="t-eyebrow">Provider</span>
            <span class="t-mono">{{ testResult.provider }}</span>
          </div>
          <div class="flex flex-col gap-1">
            <span class="t-eyebrow">Model</span>
            <span class="t-mono">{{ testResult.model }}</span>
          </div>
        </div>
        <div v-if="testResult.ok" class="flex flex-col gap-2">
          <div class="t-eyebrow">样例输出</div>
          <pre class="m-0 max-h-[260px] overflow-auto whitespace-pre-wrap break-words rounded-md border border-line bg-canvas p-4 font-mono text-xs">{{ testResult.sample_output || '(空)' }}</pre>
        </div>
        <div v-else class="flex flex-col gap-2">
          <div class="t-eyebrow">错误信息</div>
          <pre class="m-0 max-h-[260px] overflow-auto whitespace-pre-wrap break-words rounded-md border border-danger/30 bg-danger-soft p-4 font-mono text-xs text-danger">{{ testResult.error }}</pre>
        </div>
      </div>
      <template #footer>
        <UiButton
          v-if="!testing && testResult && currentTestRow"
          variant="secondary"
          @click="handleTest(currentTestRow)"
        >重新测试</UiButton>
        <UiButton variant="secondary" @click="testDialogVisible = false">关闭</UiButton>
      </template>
    </UiDialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { Plus, ChevronDown } from 'lucide-vue-next'
import { listModels, createModel, updateModel, deleteModel, testModel } from '@/api/model'
import { usePermission } from '@/composables/usePermission'
import { toast } from '@/lib/toast'
import { confirm } from '@/lib/confirm'
import UiButton from '@/components/ui/Button.vue'
import UiBadge from '@/components/ui/Badge.vue'
import UiSwitch from '@/components/ui/Switch.vue'
import UiInput from '@/components/ui/Input.vue'
import UiTextarea from '@/components/ui/Textarea.vue'
import UiInputNumber from '@/components/ui/InputNumber.vue'
import UiSelect from '@/components/ui/Select.vue'
import UiFormItem from '@/components/ui/FormItem.vue'
import UiDialog from '@/components/ui/Dialog.vue'
import UiDropdown from '@/components/ui/Dropdown.vue'
import UiDropdownItem from '@/components/ui/DropdownItem.vue'
import UiPagination from '@/components/ui/Pagination.vue'
import UiSpinner from '@/components/ui/Spinner.vue'
import UiTable, { type TableColumn } from '@/components/ui/Table.vue'

interface ModelItem {
  id: number
  display_name: string
  model_name: string
  api_protocol: string
  api_base_url: string
  api_key?: string | null
  description?: string | null
  is_active: boolean
  created_at?: string | null
  extra_params?: Record<string, unknown> | null
  [key: string]: unknown
}

interface TestResult {
  ok: boolean
  latency_ms: number
  sample_output?: string | null
  error?: string | null
  provider: string
  model: string
}

type ApiError = { response?: { data?: { message?: string } }; message?: string }

const { has } = usePermission()

const models = ref<ModelItem[]>([])
const loading = ref(false)
const page = ref(1)
const perPage = 20
const total = ref(0)
const showInactive = ref(false)

const dialogVisible = ref(false)
const editMode = ref(false)
const editId = ref<number | null>(null)
const submitting = ref(false)

// 测试相关
const testingId = ref<number | null>(null)
const testDialogVisible = ref(false)
const testResult = ref<TestResult | null>(null)
const testTargetName = ref('')
const testing = ref(false)
const currentTestRow = ref<ModelItem | null>(null)

const columns: TableColumn[] = [
  { key: 'id', label: 'ID', width: 60 },
  { key: 'display_name', label: '显示名称', minWidth: 160 },
  { key: 'model_name', label: '模型标识', minWidth: 160 },
  { key: 'api_protocol', label: '协议', width: 110 },
  { key: 'api_base_url', label: 'API 地址', minWidth: 220 },
  { key: 'is_active', label: '状态', width: 90 },
  { key: 'created_at', label: '创建时间', minWidth: 160 },
  { key: 'actions', label: '操作', width: 150, fixed: 'right' },
]

const protocolOptions = [
  { label: 'OpenAI 兼容', value: 'openai' },
  { label: 'Anthropic', value: 'anthropic' },
  { label: 'Gemini', value: 'gemini' },
  { label: 'Ollama', value: 'ollama' },
  { label: '自定义', value: 'custom' },
]

interface ModelForm {
  display_name: string
  model_name: string
  api_protocol: string
  api_base_url: string
  api_key: string
  description: string
  is_active: boolean
  gen_temperature: number | null
  gen_top_p: number | null
  gen_max_tokens: number | null
  gen_stop_sequences: string
}

const form = reactive<ModelForm>({
  display_name: '',
  model_name: '',
  api_protocol: 'openai',
  api_base_url: '',
  api_key: '',
  description: '',
  is_active: true,
  gen_temperature: null,
  gen_top_p: null,
  gen_max_tokens: null,
  gen_stop_sequences: '',
})

function formatTime(iso: string | null | undefined): string {
  return iso ? new Date(iso).toLocaleString('zh-CN') : '—'
}

function resetForm() {
  editMode.value = false
  editId.value = null
  Object.assign(form, {
    display_name: '',
    model_name: '',
    api_protocol: 'openai',
    api_base_url: '',
    api_key: '',
    description: '',
    is_active: true,
    gen_temperature: null,
    gen_top_p: null,
    gen_max_tokens: null,
    gen_stop_sequences: '',
  })
}

function openCreateDialog() {
  resetForm()
  dialogVisible.value = true
}

function openEditDialog(row: ModelItem) {
  resetForm()
  editMode.value = true
  editId.value = row.id
  const extra = (row.extra_params || {}) as Record<string, unknown>
  const stops = (extra.stop_sequences ?? extra.stop_seqs) as string[] | string | undefined
  Object.assign(form, {
    display_name: row.display_name,
    model_name: row.model_name,
    api_protocol: row.api_protocol,
    api_base_url: row.api_base_url,
    api_key: '', // never pre-fill — backend masks it
    description: row.description || '',
    is_active: row.is_active,
    gen_temperature: (extra.temperature as number | null) ?? null,
    gen_top_p: (extra.top_p as number | null) ?? null,
    gen_max_tokens: (extra.max_tokens as number | null) ?? null,
    gen_stop_sequences: Array.isArray(stops) ? stops.join(', ') : (stops || ''),
  })
  dialogVisible.value = true
}

async function fetchModels() {
  loading.value = true
  try {
    const { data } = await listModels(page.value, perPage, showInactive.value)
    models.value = data.data.items
    total.value = data.data.total
  } catch {
    toast.error('加载模型列表失败')
  } finally {
    loading.value = false
  }
}

function handleFilterChange() {
  page.value = 1
  fetchModels()
}

function onPageChange(p: number) {
  page.value = p
  fetchModels()
}

async function handleSubmit() {
  if (!form.display_name.trim()) return toast.warning('请填写显示名称')
  if (!form.model_name.trim()) return toast.warning('请填写模型标识')
  if (!form.api_base_url.trim()) return toast.warning('请填写 API 地址')

  submitting.value = true
  try {
    // 装配 extra_params
    const extra: Record<string, unknown> = {}
    if (form.gen_temperature !== null && form.gen_temperature !== undefined) {
      extra.temperature = form.gen_temperature
    }
    if (form.gen_top_p !== null && form.gen_top_p !== undefined) {
      extra.top_p = form.gen_top_p
    }
    if (form.gen_max_tokens !== null && form.gen_max_tokens !== undefined) {
      extra.max_tokens = form.gen_max_tokens
    }
    const stops = (form.gen_stop_sequences || '').split(',').map((s) => s.trim()).filter(Boolean)
    if (stops.length) extra.stop_sequences = stops

    const payload: Record<string, unknown> = {
      display_name: form.display_name.trim(),
      model_name: form.model_name.trim(),
      api_protocol: form.api_protocol,
      api_base_url: form.api_base_url.trim(),
      description: form.description.trim() || null,
      extra_params: extra,
    }
    if (form.api_key.trim()) {
      payload.api_key = form.api_key.trim()
    }
    if (editMode.value) {
      payload.is_active = form.is_active
      await updateModel(editId.value as number, payload)
      toast.success('已保存')
    } else {
      await createModel(payload)
      toast.success('模型已添加')
    }
    dialogVisible.value = false
    page.value = 1
    await fetchModels()
  } catch (err: unknown) {
    const e = err as ApiError
    toast.error(e.response?.data?.message || '操作失败')
  } finally {
    submitting.value = false
  }
}

async function toggleActive(row: ModelItem) {
  try {
    await updateModel(row.id, { is_active: !row.is_active })
    row.is_active = !row.is_active
    toast.success(row.is_active ? '已启用' : '已停用')
  } catch (err: unknown) {
    const e = err as ApiError
    toast.error(e.response?.data?.message || '操作失败')
  }
}

async function handleTest(row: ModelItem) {
  // 立即打开弹窗，进入测试中状态
  currentTestRow.value = row
  testingId.value = row.id
  testTargetName.value = row.display_name
  testResult.value = null
  testing.value = true
  testDialogVisible.value = true
  try {
    const { data } = await testModel(row.id)
    testResult.value = data.data
    if (testResult.value?.ok) {
      toast.success(`测试通过（${testResult.value.latency_ms}ms）`)
    } else {
      toast.warning('测试失败，请查看错误详情')
    }
  } catch (err: unknown) {
    const e = err as ApiError
    testResult.value = {
      ok: false,
      latency_ms: 0,
      sample_output: null,
      error: e.response?.data?.message || e.message || '请求失败',
      provider: row.api_protocol,
      model: row.model_name,
    }
    toast.error(e.response?.data?.message || '测试请求失败')
  } finally {
    testing.value = false
    testingId.value = null
  }
}

async function handleDelete(row: ModelItem) {
  const ok = await confirm({
    message: `确定删除模型「${row.display_name}」？删除后不可恢复，已关联该模型的历史任务不受影响。`,
    title: '删除确认',
    confirmText: '确认删除',
    tone: 'danger',
  })
  if (!ok) return
  try {
    await deleteModel(row.id)
    models.value = models.value.filter((m) => m.id !== row.id)
    total.value--
    toast.success('已删除')
  } catch (err: unknown) {
    const e = err as ApiError
    toast.error(e.response?.data?.message || '删除失败')
  }
}

onMounted(fetchModels)
</script>
