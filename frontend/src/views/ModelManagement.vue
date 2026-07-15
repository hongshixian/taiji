<template>
  <div class="page-shell page-shell--wide flex flex-col gap-8">
    <header class="page-header">
      <span class="page-header__eyebrow t-eyebrow">{{ t('model.eyebrow') }}</span>
      <div class="flex items-center justify-between gap-6">
        <h1 class="page-header__title">{{ t('model.title') }}</h1>
        <UiButton v-if="has('model:write')" @click="openCreateDialog">
          <Plus class="size-4" />{{ t('model.add') }}
        </UiButton>
      </div>
      <p class="page-header__lede">
        {{ t('model.lede') }}
      </p>
    </header>

    <section
      v-if="loading || models.length"
      class="flex flex-col gap-6 rounded-lg border border-line bg-surface p-6 shadow-xs"
    >
      <div class="flex items-center gap-4">
        <label class="flex cursor-pointer items-center gap-2">
          <UiSwitch v-model="showInactive" @update:model-value="handleFilterChange" />
          <span class="text-xs text-fg-tertiary">{{ t('model.showInactive') }}</span>
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
          <UiBadge :tone="value ? 'success' : 'danger'">{{ value ? t('common.enabled') : t('common.disabled') }}</UiBadge>
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
            >{{ t('model.testBtn') }}</UiButton>
            <UiButton
              v-if="has('model:write')"
              variant="text"
              size="sm"
              @click="openEditDialog(row as ModelItem)"
            >{{ t('common.edit') }}</UiButton>
            <UiDropdown v-if="has('model:write') || has('model:delete')">
              <template #trigger>
                <UiButton variant="text" size="sm">{{ t('common.more') }}<ChevronDown class="size-4" /></UiButton>
              </template>
              <template #default="{ close }">
                <UiDropdownItem
                  v-if="has('model:write')"
                  @select="close(); toggleActive(row as ModelItem)"
                >{{ (row as ModelItem).is_active ? t('common.disabled') : t('common.enabled') }}</UiDropdownItem>
                <UiDropdownItem
                  v-if="has('model:delete')"
                  danger
                  @select="close(); handleDelete(row as ModelItem)"
                >{{ t('common.delete') }}</UiDropdownItem>
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
      <span class="t-eyebrow">{{ t('model.empty.eyebrow') }}</span>
      <h3 class="m-0 text-2xl text-fg">{{ t('model.empty.title') }}</h3>
      <p class="m-0 max-w-[48ch] text-fg-secondary">
        {{ t('model.empty.desc') }}
      </p>
      <UiButton v-if="has('model:write')" class="mt-3" @click="openCreateDialog">
        <Plus class="size-4" />{{ t('model.empty.addFirst') }}
      </UiButton>
    </section>

    <!-- 新建 / 编辑对话框 -->
    <UiDialog
      v-model="dialogVisible"
      :title="editMode ? t('model.dialog.editTitle') : t('model.dialog.createTitle')"
      width="560px"
    >
      <div class="flex flex-col gap-4">
        <UiFormItem :label="t('model.field.displayName')" required :hint="t('model.field.displayNameHint')">
          <UiInput v-model="form.display_name" :placeholder="t('model.field.displayNamePlaceholder')" :maxlength="100" />
        </UiFormItem>
        <UiFormItem :label="t('model.field.modelName')" required :hint="t('model.field.modelNameHint')">
          <UiInput v-model="form.model_name" class="font-mono" :placeholder="t('model.field.modelNamePlaceholder')" :maxlength="200" />
        </UiFormItem>
        <UiFormItem :label="t('model.field.protocol')" required>
          <UiSelect v-model="form.api_protocol" :options="protocolOptions" />
        </UiFormItem>
        <UiFormItem :label="t('model.field.apiUrl')" required>
          <UiInput
            v-model="form.api_base_url"
            class="font-mono"
            placeholder="https://api.openai.com/v1"
            :maxlength="500"
          />
        </UiFormItem>
        <UiFormItem :label="t('model.field.apiKey')">
          <UiInput
            v-model="form.api_key"
            type="password"
            class="font-mono"
            :placeholder="editMode ? t('model.field.apiKeyPlaceholderEdit') : t('model.field.apiKeyPlaceholderCreate')"
            :maxlength="500"
          />
        </UiFormItem>
        <UiFormItem :label="t('common.description')">
          <UiTextarea v-model="form.description" :rows="2" :placeholder="t('model.field.descPlaceholder')" :maxlength="500" />
        </UiFormItem>

        <div class="my-2 flex items-center gap-3 text-xs font-semibold text-fg-tertiary">
          <span>{{ t('model.field.genParams') }}</span><span class="h-px flex-1 bg-line" />
        </div>
        <p class="-mt-2 text-xs leading-relaxed text-fg-tertiary">
          {{ t('model.field.genParamsHint') }}
        </p>
        <div class="grid grid-cols-1 gap-x-6 gap-y-4 sm:grid-cols-2">
          <UiFormItem label="Temperature">
            <UiInputNumber
              v-model="form.gen_temperature"
              :min="0" :max="2" :step="0.1" :precision="2"
              block :placeholder="t('model.field.optionalPlaceholder')"
            />
          </UiFormItem>
          <UiFormItem label="Top-P">
            <UiInputNumber
              v-model="form.gen_top_p"
              :min="0" :max="1" :step="0.05" :precision="2"
              block :placeholder="t('model.field.optionalPlaceholder')"
            />
          </UiFormItem>
          <UiFormItem label="Max Tokens">
            <UiInputNumber
              v-model="form.gen_max_tokens"
              :min="1" :max="200000" :step="256"
              block :placeholder="t('model.field.optionalPlaceholder')"
            />
          </UiFormItem>
          <UiFormItem :label="t('model.field.stopSeq')">
            <UiInput v-model="form.gen_stop_sequences" :placeholder="t('model.field.stopPlaceholder')" />
          </UiFormItem>
        </div>

        <UiFormItem v-if="editMode" :label="t('common.status')">
          <label class="flex items-center gap-2">
            <UiSwitch v-model="form.is_active" />
            <span class="text-sm text-fg-secondary">{{ form.is_active ? t('common.enabled') : t('common.disabled') }}</span>
          </label>
        </UiFormItem>
      </div>
      <template #footer>
        <UiButton variant="secondary" @click="dialogVisible = false">{{ t('common.cancel') }}</UiButton>
        <UiButton :loading="submitting" @click="handleSubmit">
          {{ editMode ? t('common.save') : t('common.add') }}
        </UiButton>
      </template>
    </UiDialog>

    <!-- 测试结果对话框 -->
    <UiDialog v-model="testDialogVisible" :title="t('model.test.title')" width="600px">
      <!-- 测试进行中 -->
      <div v-if="testing" class="flex min-h-[140px] flex-col items-center justify-center gap-4">
        <UiSpinner :size="28" />
        <span class="text-xs text-fg-tertiary">{{ t('model.test.sending') }}</span>
        <span class="text-xs text-fg-tertiary">{{ t('model.test.modelLabel', { name: testTargetName }) }}</span>
      </div>

      <!-- 测试结果 -->
      <div v-else-if="testResult" class="flex flex-col gap-5">
        <div class="flex items-center gap-4">
          <UiBadge :tone="testResult.ok ? 'success' : 'danger'">
            {{ testResult.ok ? t('model.test.pass') : t('model.test.fail') }}
          </UiBadge>
          <span class="text-xs text-fg-tertiary">{{ t('model.test.modelLabel', { name: testTargetName }) }}</span>
        </div>
        <div class="grid grid-cols-[repeat(auto-fit,minmax(150px,1fr))] gap-4 rounded-md border border-line bg-canvas p-4">
          <div class="flex flex-col gap-1">
            <span class="t-eyebrow">{{ t('model.test.latency') }}</span>
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
          <div class="t-eyebrow">{{ t('model.test.sampleOutput') }}</div>
          <pre class="m-0 max-h-[260px] overflow-auto whitespace-pre-wrap break-words rounded-md border border-line bg-canvas p-4 font-mono text-xs">{{ testResult.sample_output || t('model.test.emptyOutput') }}</pre>
        </div>
        <div v-else class="flex flex-col gap-2">
          <div class="t-eyebrow">{{ t('model.test.errorInfo') }}</div>
          <pre class="m-0 max-h-[260px] overflow-auto whitespace-pre-wrap break-words rounded-md border border-danger/30 bg-danger-soft p-4 font-mono text-xs text-danger">{{ testResult.error }}</pre>
        </div>
      </div>
      <template #footer>
        <UiButton
          v-if="!testing && testResult && currentTestRow"
          variant="secondary"
          @click="handleTest(currentTestRow)"
        >{{ t('model.test.retest') }}</UiButton>
        <UiButton variant="secondary" @click="testDialogVisible = false">{{ t('common.close') }}</UiButton>
      </template>
    </UiDialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
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
const { t } = useI18n()

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

const columns = computed<TableColumn[]>(() => [
  { key: 'id', label: 'ID', width: 60 },
  { key: 'display_name', label: t('model.col.displayName'), minWidth: 160 },
  { key: 'model_name', label: t('model.col.modelName'), minWidth: 160 },
  { key: 'api_protocol', label: t('model.col.protocol'), width: 110 },
  { key: 'api_base_url', label: t('model.col.apiUrl'), minWidth: 220 },
  { key: 'is_active', label: t('common.status'), width: 90 },
  { key: 'created_at', label: t('common.createdAt'), minWidth: 160 },
  { key: 'actions', label: t('common.actions'), width: 150, fixed: 'right' },
])

const protocolOptions = computed(() => [
  { label: t('model.proto.openai'), value: 'openai' },
  { label: 'Anthropic', value: 'anthropic' },
  { label: 'Gemini', value: 'gemini' },
  { label: 'Ollama', value: 'ollama' },
  { label: t('model.proto.custom'), value: 'custom' },
])

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
    toast.error(t('model.toast.loadFailed'))
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
  if (!form.display_name.trim()) return toast.warning(t('model.toast.fillDisplayName'))
  if (!form.model_name.trim()) return toast.warning(t('model.toast.fillModelName'))
  if (!form.api_base_url.trim()) return toast.warning(t('model.toast.fillApiUrl'))

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
      toast.success(t('common.saveSuccess'))
    } else {
      await createModel(payload)
      toast.success(t('model.toast.added'))
    }
    dialogVisible.value = false
    page.value = 1
    await fetchModels()
  } catch (err: unknown) {
    const e = err as ApiError
    toast.error(e.response?.data?.message || t('common.operationFailed'))
  } finally {
    submitting.value = false
  }
}

async function toggleActive(row: ModelItem) {
  try {
    await updateModel(row.id, { is_active: !row.is_active })
    row.is_active = !row.is_active
    toast.success(row.is_active ? t('common.active') : t('common.inactive'))
  } catch (err: unknown) {
    const e = err as ApiError
    toast.error(e.response?.data?.message || t('common.operationFailed'))
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
      toast.success(t('model.toast.testPass', { ms: testResult.value.latency_ms }))
    } else {
      toast.warning(t('model.toast.testFail'))
    }
  } catch (err: unknown) {
    const e = err as ApiError
    testResult.value = {
      ok: false,
      latency_ms: 0,
      sample_output: null,
      error: e.response?.data?.message || e.message || t('model.toast.reqFailed'),
      provider: row.api_protocol,
      model: row.model_name,
    }
    toast.error(e.response?.data?.message || t('model.toast.testReqFailed'))
  } finally {
    testing.value = false
    testingId.value = null
  }
}

async function handleDelete(row: ModelItem) {
  const ok = await confirm({
    message: t('model.remove.message', { name: row.display_name }),
    title: t('model.remove.title'),
    confirmText: t('model.remove.confirmText'),
    tone: 'danger',
  })
  if (!ok) return
  try {
    await deleteModel(row.id)
    models.value = models.value.filter((m) => m.id !== row.id)
    total.value--
    toast.success(t('common.deleteSuccess'))
  } catch (err: unknown) {
    const e = err as ApiError
    toast.error(e.response?.data?.message || t('common.operationFailed'))
  }
}

onMounted(fetchModels)
</script>
