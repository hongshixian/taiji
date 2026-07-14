<template>
  <div class="page-shell page-shell--wide audit-log-management">
    <header class="page-header">
      <span class="page-header__eyebrow t-eyebrow">审计 · 平台日志</span>
      <div class="page-header__row">
        <h1 class="page-header__title">审计日志</h1>
        <el-button :loading="loading" @click="fetchLogs">
          <el-icon><Refresh /></el-icon>&nbsp;刷新
        </el-button>
      </div>
      <p class="page-header__lede">
        平台管理操作的不可变记录。租户管理员只看本租户；超级管理员可跨租户查询。
      </p>
    </header>

    <section class="filters">
      <el-select
        v-if="authStore.isSuperuser"
        v-model="filters.tenant_id"
        clearable
        placeholder="租户"
        class="filter-control"
      >
        <el-option
          v-for="tenant in tenants"
          :key="tenant.id"
          :label="tenant.name"
          :value="tenant.id"
        />
      </el-select>
      <el-select v-model="filters.action" clearable filterable placeholder="操作" class="filter-control">
        <el-option v-for="item in actionOptions" :key="item" :label="item" :value="item" />
      </el-select>
      <el-select v-model="filters.resource_type" clearable placeholder="资源" class="filter-control">
        <el-option v-for="item in resourceOptions" :key="item" :label="item" :value="item" />
      </el-select>
      <el-input v-model="filters.actor_user_id" clearable placeholder="操作者 ID" class="small-control" />
      <el-input v-model="filters.resource_id" clearable placeholder="资源 ID" class="small-control" />
      <el-date-picker
        v-model="dateRange"
        type="datetimerange"
        start-placeholder="开始时间"
        end-placeholder="结束时间"
        value-format="YYYY-MM-DDTHH:mm:ss"
        class="date-control"
      />
      <el-button type="primary" @click="handleSearch">
        <el-icon><Search /></el-icon>&nbsp;查询
      </el-button>
      <el-button @click="resetFilters">
        <el-icon><RefreshLeft /></el-icon>&nbsp;重置
      </el-button>
    </section>

    <section class="data-section" data-density="compact">
      <el-table :data="logs" stripe v-loading="loading" class="audit-table">
        <el-table-column type="expand">
          <template #default="{ row }">
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
        </el-table-column>
        <el-table-column label="时间" width="160">
          <template #default="{ row }"><span class="t-mono">{{ formatTime(row.created_at) }}</span></template>
        </el-table-column>
        <el-table-column label="操作者" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">
            <span>{{ row.actor_username || '—' }}</span>
            <span v-if="row.actor_is_superuser" class="status-pill status-pill--inline" data-tone="danger">超管</span>
          </template>
        </el-table-column>
        <el-table-column label="租户" min-width="110" show-overflow-tooltip>
          <template #default="{ row }">{{ row.tenant_name || platformLabel(row) }}</template>
        </el-table-column>
        <el-table-column prop="action" label="操作" min-width="140" show-overflow-tooltip>
          <template #default="{ row }"><span class="t-mono">{{ row.action }}</span></template>
        </el-table-column>
        <el-table-column prop="resource_type" label="资源" min-width="100" show-overflow-tooltip>
          <template #default="{ row }"><span class="t-mono">{{ row.resource_type }}</span></template>
        </el-table-column>
        <el-table-column label="对象" min-width="130" show-overflow-tooltip>
          <template #default="{ row }">
            <span>{{ row.resource_name || row.resource_id || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="结果" width="100">
          <template #default="{ row }">
            <span class="status-pill" :data-tone="row.result === 'success' ? 'success' : 'danger'">
              {{ row.result }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="ip_address" label="IP" width="120">
          <template #default="{ row }"><span class="t-mono">{{ row.ip_address || '—' }}</span></template>
        </el-table-column>
      </el-table>

      <div class="pagination-row">
        <el-pagination
          background
          layout="total, sizes, prev, pager, next"
          :total="total"
          :page-size="pagination.per_page"
          :page-sizes="[10, 20, 50]"
          :current-page="pagination.page"
          @current-change="handlePageChange"
          @size-change="handleSizeChange"
        />
      </div>
    </section>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { listAuditLogs } from '../api/audit'
import { listTenants } from '../api/superadmin'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const loading = ref(false)
const logs = ref([])
const total = ref(0)
const tenants = ref([])
const dateRange = ref([])

const pagination = reactive({
  page: 1,
  per_page: 20,
})

const filters = reactive({
  tenant_id: null,
  action: '',
  resource_type: '',
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

function buildParams() {
  const params = {
    page: pagination.page,
    per_page: pagination.per_page,
  }
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== null && value !== '') params[key] = value
  })
  if (dateRange.value?.length === 2) {
    params.date_from = dateRange.value[0]
    params.date_to = dateRange.value[1]
  }
  return params
}

async function fetchLogs() {
  loading.value = true
  try {
    const { data } = await listAuditLogs(buildParams())
    logs.value = data.data.items
    total.value = data.data.total
  } catch (err) {
    ElMessage.error(err.response?.data?.message || '加载审计日志失败')
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
  filters.action = ''
  filters.resource_type = ''
  filters.actor_user_id = ''
  filters.resource_id = ''
  dateRange.value = []
  handleSearch()
}

function handlePageChange(page) {
  pagination.page = page
  fetchLogs()
}

function handleSizeChange(size) {
  pagination.per_page = size
  pagination.page = 1
  fetchLogs()
}

function formatJson(value) {
  if (!value) return '-'
  return JSON.stringify(value, null, 2)
}

function formatTime(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

function platformLabel(row) {
  return row.tenant_id === null || row.tenant_id === undefined ? '平台级' : `租户 #${row.tenant_id}`
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
.filter-control { width: 180px; }
.small-control { width: 140px; }
.date-control { width: 360px; max-width: 100%; }

.data-section { display: flex; flex-direction: column; gap: var(--space-5); }
.audit-table {
  width: 100%;
  border-radius: var(--radius-lg);
  overflow: hidden;
  border: 1px solid var(--border-subtle);
}

.status-pill {
  display: inline-flex;
  align-items: center;
  padding: 2px var(--space-5);
  border-radius: var(--radius-full);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  background: var(--badge-bg-neutral);
  color: var(--badge-fg-neutral);
  border: 1px solid transparent;
  white-space: nowrap;
}
.status-pill[data-tone='success'] {
  background: var(--color-success-bg);
  color: var(--color-success-fg);
  border-color: var(--color-success-border);
}
.status-pill[data-tone='danger'] {
  background: var(--color-danger-bg);
  color: var(--color-danger-fg);
  border-color: var(--color-danger-border);
}
.status-pill--inline { margin-left: var(--space-3); }

.detail-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-6);
  padding: var(--space-3) var(--space-7) var(--space-7) var(--space-11);
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
.pagination-row { display: flex; justify-content: flex-end; }

@media (max-width: 900px) {
  .filter-control,
  .small-control,
  .date-control { width: 100%; }
  .detail-grid { grid-template-columns: 1fr; padding-left: var(--space-7); }
}
@media (max-width: 768px) {
  .page-header__row { flex-direction: column; align-items: flex-start; }
}
</style>
