<template>
  <div class="page-shell page-shell--wide audit-log-management">
    <header class="page-header">
      <span class="page-header__eyebrow t-eyebrow">审计 · 平台日志</span>
      <div class="page-header__row">
        <h1 class="page-header__title">审计日志</h1>
        <UiButton variant="secondary" :loading="loading" @click="fetchLogs">
          <template #icon><RefreshCw class="size-4" /></template>
          刷新
        </UiButton>
      </div>
      <p class="page-header__lede">
        平台管理操作的不可变记录。租户管理员只看本租户；超级管理员可跨租户查询。
      </p>
    </header>

    <section class="filters">
      <UiSelect
        v-if="authStore.isSuperuser"
        v-model="filters.tenant_id"
        :options="tenantOptions"
        clearable
        placeholder="租户"
        class="filter-control"
      />
      <UiSelect
        v-model="filters.action"
        :options="actionSelectOptions"
        clearable
        filterable
        placeholder="操作"
        class="filter-control"
      />
      <UiSelect
        v-model="filters.resource_type"
        :options="resourceSelectOptions"
        clearable
        placeholder="资源"
        class="filter-control"
      />
      <UiInput v-model="filters.actor_user_id" placeholder="操作者 ID" class="small-control" />
      <UiInput v-model="filters.resource_id" placeholder="资源 ID" class="small-control" />
      <input v-model="dateFrom" type="datetime-local" class="date-input" />
      <span class="text-fg-tertiary">—</span>
      <input v-model="dateTo" type="datetime-local" class="date-input" />
      <UiButton @click="handleSearch">
        <template #icon><Search class="size-4" /></template>
        查询
      </UiButton>
      <UiButton variant="secondary" @click="resetFilters">
        <template #icon><RotateCcw class="size-4" /></template>
        重置
      </UiButton>
    </section>

    <section class="data-section" data-density="compact">
      <UiTable
        :columns="columns"
        :data="logs"
        row-key="id"
        stripe
        :loading="loading"
        expandable
        v-model:expanded-keys="expandedKeys"
      >
        <template #cell-created_at="{ row }">
          <span class="t-mono">{{ formatTime(row.created_at) }}</span>
        </template>
        <template #cell-actor="{ row }">
          <span>{{ row.actor_username || '—' }}</span>
          <UiBadge v-if="row.actor_is_superuser" tone="danger" class="ml-2">超管</UiBadge>
        </template>
        <template #cell-tenant="{ row }">
          {{ row.tenant_name || platformLabel(row) }}
        </template>
        <template #cell-action="{ row }">
          <span class="t-mono">{{ row.action }}</span>
        </template>
        <template #cell-resource_type="{ row }">
          <span class="t-mono">{{ row.resource_type }}</span>
        </template>
        <template #cell-object="{ row }">
          <span>{{ row.resource_name || row.resource_id || '—' }}</span>
        </template>
        <template #cell-result="{ row }">
          <UiBadge :tone="row.result === 'success' ? 'success' : 'danger'">
            {{ row.result }}
          </UiBadge>
        </template>
        <template #cell-ip_address="{ row }">
          <span class="t-mono">{{ row.ip_address || '—' }}</span>
        </template>
        <template #expand="{ row }">
          <div class="detail-grid">
            <div class="detail-block">
              <span class="t-eyebrow detail-title">变更前</span>
              <pre>{{ formatJson(row.before_data) }}</pre>
            </div>
            <div class="detail-block">
              <span class="t-eyebrow detail-title">变更后</span>
              <pre>{{ formatJson(row.after_data) }}</pre>
            </div>
            <div class="detail-block">
              <span class="t-eyebrow detail-title">上下文</span>
              <pre>{{ formatJson(row.metadata) }}</pre>
            </div>
          </div>
        </template>
      </UiTable>

      <div class="pagination-row">
        <UiSelect
          :model-value="pagination.per_page"
          :options="pageSizeOptions"
          class="page-size-control"
          @update:model-value="handleSizeChange"
        />
        <UiPagination
          :total="total"
          :page-size="pagination.per_page"
          :current-page="pagination.page"
          @current-change="handlePageChange"
        />
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, computed } from 'vue'
import { RefreshCw, RotateCcw, Search } from 'lucide-vue-next'
import { toast } from '@/lib/toast'
import { listAuditLogs } from '@/api/audit'
import { listTenants } from '@/api/superadmin'
import { useAuthStore } from '@/stores/auth'
import UiTable, { type TableColumn } from '@/components/ui/Table.vue'
import UiButton from '@/components/ui/Button.vue'
import UiBadge from '@/components/ui/Badge.vue'
import UiPagination from '@/components/ui/Pagination.vue'
import UiInput from '@/components/ui/Input.vue'
import UiSelect, { type SelectOption } from '@/components/ui/Select.vue'

const authStore = useAuthStore()

interface AuditRow {
  id: number
  created_at?: string
  actor_username?: string
  actor_is_superuser?: boolean
  tenant_id?: number | null
  tenant_name?: string
  action?: string
  resource_type?: string
  resource_id?: string | number
  resource_name?: string
  result?: string
  ip_address?: string
  before_data?: unknown
  after_data?: unknown
  metadata?: unknown
  [key: string]: unknown
}
interface TenantOption {
  id: number
  name: string
}

const loading = ref(false)
const logs = ref<AuditRow[]>([])
const total = ref(0)
const tenants = ref<TenantOption[]>([])
const dateFrom = ref('')
const dateTo = ref('')
const expandedKeys = ref<(string | number)[]>([])

const columns: TableColumn[] = [
  { key: 'created_at', label: '时间', width: 160 },
  { key: 'actor', label: '操作者', minWidth: 120, prop: 'actor_username', tooltip: true },
  { key: 'tenant', label: '租户', minWidth: 110, prop: 'tenant_name', tooltip: true },
  { key: 'action', label: '操作', minWidth: 140, tooltip: true },
  { key: 'resource_type', label: '资源', minWidth: 100, tooltip: true },
  { key: 'object', label: '对象', minWidth: 130, prop: 'resource_name', tooltip: true },
  { key: 'result', label: '结果', width: 100 },
  { key: 'ip_address', label: 'IP', width: 120 },
]

const pagination = reactive({
  page: 1,
  per_page: 20,
})

const filters = reactive({
  tenant_id: null as number | null,
  action: null as string | null,
  resource_type: null as string | null,
  actor_user_id: '',
  resource_id: '',
})

const actionOptions = [
  'tenant.create',
  'tenant.update',
  'tenant.delete',
  'tenant_member.add',
  'tenant_member.remove',
  'user.create',
  'user.update',
  'user.disable',
  'user.enable',
  'user.delete',
  'role.create',
  'role.update',
  'role.delete',
  'system_setting.update',
  'superuser.grant',
  'superuser.revoke',
  'password.change',
]

const resourceOptions = ['tenant', 'tenant_member', 'user', 'role', 'system_setting']

const tenantOptions = computed<SelectOption[]>(() =>
  tenants.value.map((t) => ({ label: t.name, value: t.id })),
)
const actionSelectOptions: SelectOption[] = actionOptions.map((a) => ({ label: a, value: a }))
const resourceSelectOptions: SelectOption[] = resourceOptions.map((r) => ({ label: r, value: r }))
const pageSizeOptions: SelectOption[] = [10, 20, 50].map((n) => ({ label: `${n} 条/页`, value: n }))

function buildParams() {
  const params: Record<string, unknown> = {
    page: pagination.page,
    per_page: pagination.per_page,
  }
  ;(Object.entries(filters) as [string, unknown][]).forEach(([key, value]) => {
    if (value !== null && value !== '') params[key] = value
  })
  if (dateFrom.value && dateTo.value) {
    params.date_from = dateFrom.value
    params.date_to = dateTo.value
  }
  return params
}

async function fetchLogs() {
  loading.value = true
  try {
    const { data } = await listAuditLogs(buildParams())
    logs.value = data.data.items
    total.value = data.data.total
  } catch (err: unknown) {
    const e = err as { response?: { data?: { message?: string } } }
    toast.error(e.response?.data?.message || '加载审计日志失败')
  } finally {
    loading.value = false
  }
}

async function fetchTenants() {
  if (!authStore.isSuperuser) return
  try {
    const { data } = await listTenants()
    tenants.value = data.data
  } catch {
    tenants.value = []
  }
}

function handleSearch() {
  pagination.page = 1
  fetchLogs()
}

function resetFilters() {
  filters.tenant_id = null
  filters.action = null
  filters.resource_type = null
  filters.actor_user_id = ''
  filters.resource_id = ''
  dateFrom.value = ''
  dateTo.value = ''
  handleSearch()
}

function handlePageChange(page: number) {
  pagination.page = page
  fetchLogs()
}

function handleSizeChange(size: string | number | null) {
  pagination.per_page = Number(size)
  pagination.page = 1
  fetchLogs()
}

function formatJson(value: unknown) {
  if (!value) return '-'
  return JSON.stringify(value, null, 2)
}

function formatTime(value?: unknown) {
  if (!value) return '-'
  return new Date(value as string).toLocaleString()
}

function platformLabel(row: Record<string, unknown>) {
  const r = row as AuditRow
  return r.tenant_id === null || r.tenant_id === undefined ? '平台级' : `租户 #${r.tenant_id}`
}

onMounted(async () => {
  await Promise.all([fetchLogs(), fetchTenants()])
})
</script>

<style scoped>
.audit-log-management {
  display: flex;
  flex-direction: column;
  gap: var(--space-9);
}
.page-header__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-7);
}

.filters {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-5);
  align-items: center;
  padding: var(--space-6) var(--space-7);
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xs);
}
.filter-control {
  width: 180px;
}
.small-control {
  width: 140px;
}
.date-input {
  height: 2.25rem;
  padding: 0 0.75rem;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  background: var(--bg-surface);
  color: var(--fg-primary);
  font-size: var(--text-sm);
}

.data-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-6);
}
.detail-block {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.detail-title {
  letter-spacing: 0.18em;
}
pre {
  margin: 0;
  min-height: 80px;
  max-height: 260px;
  overflow: auto;
  padding: var(--space-5);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  background: var(--bg-surface-sunken);
  color: var(--fg-primary);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: var(--leading-normal);
}
.pagination-row {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: var(--space-5);
}
.page-size-control {
  width: 120px;
}

@media (max-width: 900px) {
  .filter-control,
  .small-control,
  .date-input {
    width: 100%;
  }
  .detail-grid {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 768px) {
  .page-header__row {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
