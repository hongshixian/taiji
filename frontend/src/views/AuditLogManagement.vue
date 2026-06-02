<template>
  <div class="audit-log-management">
    <div class="top-bar">
      <div class="page-title">
        <el-icon class="page-icon"><Tickets /></el-icon>
        <h2>审计日志</h2>
      </div>
      <el-button :loading="loading" @click="fetchLogs">
        <el-icon><Refresh /></el-icon>
      </el-button>
    </div>

    <div class="filters">
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
        <el-icon><Search /></el-icon>
      </el-button>
      <el-button @click="resetFilters">
        <el-icon><RefreshLeft /></el-icon>
      </el-button>
    </div>

    <el-table :data="logs" stripe v-loading="loading" class="audit-table">
      <el-table-column type="expand">
        <template #default="{ row }">
          <div class="detail-grid">
            <div>
              <div class="detail-title">变更前</div>
              <pre>{{ formatJson(row.before_data) }}</pre>
            </div>
            <div>
              <div class="detail-title">变更后</div>
              <pre>{{ formatJson(row.after_data) }}</pre>
            </div>
            <div>
              <div class="detail-title">上下文</div>
              <pre>{{ formatJson(row.metadata) }}</pre>
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="时间" width="180">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作者" min-width="130">
        <template #default="{ row }">
          <span>{{ row.actor_username || '-' }}</span>
          <el-tag v-if="row.actor_is_superuser" size="small" type="danger" class="tag-gap">超管</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="租户" min-width="120">
        <template #default="{ row }">{{ row.tenant_name || platformLabel(row) }}</template>
      </el-table-column>
      <el-table-column prop="action" label="操作" min-width="150" />
      <el-table-column prop="resource_type" label="资源" width="120" />
      <el-table-column label="对象" min-width="150">
        <template #default="{ row }">
          <span>{{ row.resource_name || row.resource_id || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="结果" width="90">
        <template #default="{ row }">
          <el-tag :type="row.result === 'success' ? 'success' : 'danger'" size="small">
            {{ row.result }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="ip_address" label="IP" width="130" />
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
.audit-log-management { max-width: 1280px; margin: 0 auto; }
.top-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; }
.page-title { display: flex; align-items: center; gap: 10px; }
.page-title h2 { margin: 0; font-weight: 600; color: var(--el-text-color-primary); }
.page-icon { font-size: 22px; color: var(--taiji-accent); }

.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  margin-bottom: 14px;
}
.filter-control { width: 170px; }
.small-control { width: 130px; }
.date-control { width: 360px; max-width: 100%; }

.audit-table { width: 100%; }
.tag-gap { margin-left: 6px; }
.detail-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  padding: 6px 18px 14px 48px;
}
.detail-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin-bottom: 6px;
}
pre {
  margin: 0;
  min-height: 80px;
  max-height: 260px;
  overflow: auto;
  padding: 10px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
  background: var(--el-fill-color-lighter);
  color: var(--el-text-color-regular);
  font-size: 12px;
  line-height: 1.45;
}
.pagination-row { display: flex; justify-content: flex-end; margin-top: 16px; }

@media (max-width: 900px) {
  .filter-control,
  .small-control,
  .date-control { width: 100%; }
  .detail-grid { grid-template-columns: 1fr; padding-left: 18px; }
}
</style>
