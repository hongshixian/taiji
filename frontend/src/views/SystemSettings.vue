<template>
  <div class="page-shell flex max-w-[960px] flex-col gap-8">
    <header class="page-header">
      <span class="page-header__eyebrow t-eyebrow">{{ t('systemSettings.eyebrow') }}</span>
      <h1 class="page-header__title">{{ t('systemSettings.title') }}</h1>
      <p class="page-header__lede">
        {{ t('systemSettings.lede') }}
      </p>
    </header>

    <!-- 注册策略 -->
    <section class="relative flex flex-col gap-7 rounded-lg border border-line bg-surface p-8 shadow-xs">
      <div
        v-if="loading"
        class="absolute inset-0 z-10 flex items-center justify-center rounded-lg bg-surface/60 backdrop-blur-[1px]"
      >
        <UiSpinner :size="28" />
      </div>
      <header class="flex flex-col gap-3">
        <span class="t-eyebrow">{{ t('systemSettings.registration.eyebrow') }}</span>
        <h2 class="m-0 text-2xl font-bold tracking-tight text-fg">{{ t('systemSettings.registration.title') }}</h2>
        <p class="m-0 max-w-[56ch] text-sm text-fg-secondary">
          {{ t('systemSettings.registration.desc') }}
        </p>
      </header>

      <div class="flex max-w-[620px] flex-col gap-5">
        <UiFormItem :label="t('systemSettings.registration.defaultTenant')">
          <div class="max-w-[420px]">
            <UiSelect v-model="form.defaultRegistrationTenantSlug" :options="tenantOptions" filterable />
          </div>
        </UiFormItem>
        <div>
          <UiButton :loading="saving" @click="saveSettings">{{ t('common.save') }}</UiButton>
        </div>
      </div>
    </section>

    <!-- Benchmark 集成 -->
    <section class="relative flex flex-col gap-7 rounded-lg border border-line bg-surface p-8 shadow-xs">
      <div
        v-if="loading"
        class="absolute inset-0 z-10 flex items-center justify-center rounded-lg bg-surface/60 backdrop-blur-[1px]"
      >
        <UiSpinner :size="28" />
      </div>
      <header class="flex flex-col gap-3">
        <span class="t-eyebrow">{{ t('systemSettings.benchmark.eyebrow') }}</span>
        <h2 class="m-0 text-2xl font-bold tracking-tight text-fg">{{ t('systemSettings.benchmark.title') }}</h2>
        <p class="m-0 max-w-[56ch] text-sm text-fg-secondary">
          {{ t('systemSettings.benchmark.desc') }}
        </p>
      </header>

      <div class="flex max-w-[620px] flex-col gap-5">
        <UiFormItem :label="t('systemSettings.benchmark.hfToken')" :hint="t('systemSettings.benchmark.hfTokenHint')">
          <div class="max-w-[420px]">
            <UiInput v-model="form.hfToken" type="password" :placeholder="hfTokenPlaceholder" />
          </div>
        </UiFormItem>
        <UiFormItem :label="t('systemSettings.benchmark.judgeModel')">
          <div class="max-w-[420px]">
            <UiSelect
              v-model="form.defaultJudgeModelId"
              :options="judgeModelOptions"
              filterable
              clearable
              :placeholder="t('systemSettings.benchmark.judgeModelPlaceholder')"
            />
          </div>
        </UiFormItem>
        <div>
          <UiButton :loading="savingBenchmark" @click="saveBenchmarkSettings">{{ t('common.save') }}</UiButton>
        </div>
      </div>
    </section>

    <!-- 超级管理员 -->
    <section class="flex flex-col gap-7 rounded-lg border border-line bg-surface p-8 shadow-xs">
      <header class="flex flex-col gap-7 sm:flex-row sm:items-end sm:justify-between">
        <div class="flex flex-col gap-3">
          <span class="t-eyebrow">{{ t('systemSettings.superuser.eyebrow') }}</span>
          <h2 class="m-0 text-2xl font-bold tracking-tight text-fg">{{ t('systemSettings.superuser.title') }}</h2>
          <p class="m-0 max-w-[56ch] text-sm text-fg-secondary">
            {{ t('systemSettings.superuser.desc') }}
          </p>
        </div>
        <div class="flex items-center gap-3 sm:shrink-0">
          <div class="w-[220px]">
            <UiInput
              v-model="superuserIdentifier"
              :placeholder="t('systemSettings.superuser.identifierPlaceholder')"
              @enter="handleAddSuperuser"
            />
          </div>
          <UiButton :loading="addingSuperuser" @click="handleAddSuperuser">{{ t('common.add') }}</UiButton>
        </div>
      </header>

      <UiTable
        :columns="superuserColumns"
        :data="superusers"
        row-key="id"
        stripe
        :loading="superusersLoading"
      >
        <template #cell-email="{ value }">
          <span class="t-mono">{{ value }}</span>
        </template>
        <template #cell-memberships="{ row }">
          <div class="flex flex-wrap gap-2">
            <UiBadge
              v-for="m in (row as Superuser).memberships"
              :key="m.id"
              tone="neutral"
            >{{ m.tenant_name }}</UiBadge>
          </div>
        </template>
        <template #cell-actions="{ row }">
          <UiButton
            variant="danger-text"
            size="sm"
            :disabled="(row as Superuser).id === authStore.user?.id"
            @click="handleRemoveSuperuser(row as Superuser)"
          >{{ t('systemSettings.superuser.remove') }}</UiButton>
        </template>
      </UiTable>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import {
  addSuperuser,
  listSuperusers,
  listTenants,
  listSystemSettings,
  removeSuperuser,
  updateSystemSettings,
} from '@/api/superadmin'
import { listModels } from '@/api/model'
import { toast } from '@/lib/toast'
import { confirm } from '@/lib/confirm'
import UiButton from '@/components/ui/Button.vue'
import UiBadge from '@/components/ui/Badge.vue'
import UiInput from '@/components/ui/Input.vue'
import UiSelect from '@/components/ui/Select.vue'
import UiFormItem from '@/components/ui/FormItem.vue'
import UiSpinner from '@/components/ui/Spinner.vue'
import UiTable, { type TableColumn } from '@/components/ui/Table.vue'

const DEFAULT_REGISTRATION_TENANT_KEY = 'public.default_registration_tenant_slug'
const HF_TOKEN_KEY = 'integrations.hf_token'
const DEFAULT_JUDGE_MODEL_ID_KEY = 'benchmark.default_judge_model_id'

interface Tenant {
  id: number
  name: string
  slug: string
  is_active: boolean
}
interface JudgeModel {
  id: number
  display_name: string
}
interface Membership {
  id: number
  tenant_name: string
}
interface Superuser {
  id: number
  username: string
  email: string
  memberships: Membership[]
  [key: string]: unknown
}
interface SystemSetting {
  key: string
  value: string | null
}
type ApiError = { response?: { data?: { message?: string } }; message?: string }

const authStore = useAuthStore()
const { t } = useI18n()
const loading = ref(false)
const saving = ref(false)
const savingBenchmark = ref(false)
const tenants = ref<Tenant[]>([])
const superusers = ref<Superuser[]>([])
const superusersLoading = ref(false)
const addingSuperuser = ref(false)
const superuserIdentifier = ref('')
const judgeModelCandidates = ref<JudgeModel[]>([])
const hfTokenAlreadySet = ref(false)
const form = reactive<{
  defaultRegistrationTenantSlug: string
  hfToken: string
  defaultJudgeModelId: string | number | null
}>({
  defaultRegistrationTenantSlug: '',
  hfToken: '',
  defaultJudgeModelId: null,
})

const superuserColumns = computed<TableColumn[]>(() => [
  { key: 'username', label: t('systemSettings.superuser.colUsername'), minWidth: 140 },
  { key: 'email', label: t('systemSettings.superuser.colEmail'), minWidth: 200 },
  { key: 'memberships', label: t('systemSettings.superuser.colMemberships'), minWidth: 240 },
  { key: 'actions', label: t('common.actions'), width: 110, fixed: 'right' },
])

const activeTenants = computed(() => tenants.value.filter((t) => t.is_active))
const tenantOptions = computed(() =>
  activeTenants.value.map((t) => ({ label: `${t.name} (${t.slug})`, value: t.slug })),
)
const judgeModelOptions = computed(() =>
  judgeModelCandidates.value.map((m) => ({ label: m.display_name, value: m.id })),
)
const hfTokenPlaceholder = computed(() =>
  hfTokenAlreadySet.value
    ? t('systemSettings.benchmark.hfTokenPlaceholderSet')
    : t('systemSettings.benchmark.hfTokenPlaceholderUnset'),
)

async function fetchData() {
  loading.value = true
  try {
    const [settingsResp, tenantsResp, modelsResp] = await Promise.all([
      listSystemSettings(),
      listTenants(),
      listModels(1, 200, false).catch(() => ({ data: { data: { items: [] } } })),
    ])
    tenants.value = tenantsResp.data.data || []
    judgeModelCandidates.value = modelsResp.data.data.items || []
    const settings: SystemSetting[] = settingsResp.data.data || []
    const defaultTenant = settings.find((s) => s.key === DEFAULT_REGISTRATION_TENANT_KEY)
    form.defaultRegistrationTenantSlug = defaultTenant?.value || 'guest'

    const hfSetting = settings.find((s) => s.key === HF_TOKEN_KEY)
    hfTokenAlreadySet.value = !!hfSetting?.value
    form.hfToken = ''

    const judgeSetting = settings.find((s) => s.key === DEFAULT_JUDGE_MODEL_ID_KEY)
    form.defaultJudgeModelId = judgeSetting?.value ?? null
  } catch (err: unknown) {
    const e = err as ApiError
    toast.error(e.response?.data?.message || t('common.loadFailed'))
  } finally {
    loading.value = false
  }
}

async function saveSettings() {
  if (!form.defaultRegistrationTenantSlug) {
    toast.warning(t('systemSettings.toast.selectTenant'))
    return
  }
  saving.value = true
  try {
    await updateSystemSettings({
      [DEFAULT_REGISTRATION_TENANT_KEY]: form.defaultRegistrationTenantSlug,
    })
    toast.success(t('common.saveSuccess'))
  } catch (err: unknown) {
    const e = err as ApiError
    toast.error(e.response?.data?.message || t('systemSettings.toast.saveFailed'))
  } finally {
    saving.value = false
  }
}

async function saveBenchmarkSettings() {
  const payload: Record<string, unknown> = {
    [DEFAULT_JUDGE_MODEL_ID_KEY]: form.defaultJudgeModelId ?? null,
  }
  if (form.hfToken.trim()) {
    payload[HF_TOKEN_KEY] = form.hfToken.trim()
  }
  savingBenchmark.value = true
  try {
    await updateSystemSettings(payload)
    toast.success(t('common.saveSuccess'))
    form.hfToken = ''
    fetchData()
  } catch (err: unknown) {
    const e = err as ApiError
    toast.error(e.response?.data?.message || t('systemSettings.toast.saveFailed'))
  } finally {
    savingBenchmark.value = false
  }
}

async function fetchSuperusers() {
  superusersLoading.value = true
  try {
    const { data } = await listSuperusers()
    superusers.value = data.data || []
  } catch (err: unknown) {
    const e = err as ApiError
    toast.error(e.response?.data?.message || t('systemSettings.toast.loadSuperusersFailed'))
  } finally {
    superusersLoading.value = false
  }
}

async function handleAddSuperuser() {
  const identifier = superuserIdentifier.value.trim()
  if (!identifier) {
    toast.warning(t('systemSettings.toast.enterIdentifier'))
    return
  }
  addingSuperuser.value = true
  try {
    await addSuperuser(identifier)
    superuserIdentifier.value = ''
    toast.success(t('systemSettings.toast.added'))
    fetchSuperusers()
  } catch (err: unknown) {
    const e = err as ApiError
    toast.error(e.response?.data?.message || t('systemSettings.toast.addFailed'))
  } finally {
    addingSuperuser.value = false
  }
}

async function handleRemoveSuperuser(row: Superuser) {
  const ok = await confirm({
    message: t('systemSettings.removeConfirm.message', { name: row.username }),
    title: t('systemSettings.removeConfirm.title'),
    confirmText: t('systemSettings.removeConfirm.confirmText'),
    tone: 'danger',
  })
  if (!ok) return
  try {
    await removeSuperuser(row.id)
    toast.success(t('systemSettings.toast.removed'))
    fetchSuperusers()
  } catch (err: unknown) {
    const e = err as ApiError
    toast.error(e.response?.data?.message || t('systemSettings.toast.removeFailed'))
  }
}

onMounted(() => {
  fetchData()
  fetchSuperusers()
})
</script>
