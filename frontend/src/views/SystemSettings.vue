<template>
  <div class="page-shell system-settings">
    <header class="page-header">
      <span class="page-header__eyebrow t-eyebrow">超级管理员 · 平台配置</span>
      <h1 class="page-header__title">系统设置</h1>
      <p class="page-header__lede">
        平台级 key/value 配置和超级管理员名册。修改这里的设置会影响整个平台。
      </p>
    </header>

    <section class="settings-card" v-loading="loading">
      <header class="settings-card__header">
        <span class="t-eyebrow">注册策略</span>
        <h2 class="settings-card__title">默认注册租户</h2>
        <p class="t-body-sm settings-card__lede">
          新公开注册的用户会自动加入这里选择的租户。
        </p>
      </header>

      <el-form label-width="140px" class="settings-form">
        <el-form-item label="默认租户">
          <el-select
            v-model="form.defaultRegistrationTenantSlug"
            filterable
            style="width: 320px"
          >
            <el-option
              v-for="tenant in activeTenants"
              :key="tenant.id"
              :label="`${tenant.name} (${tenant.slug})`"
              :value="tenant.slug"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="saving" @click="saveSettings">
            保存
          </el-button>
        </el-form-item>
      </el-form>
    </section>

    <section class="settings-card">
      <header class="settings-card__header settings-card__header--row">
        <div>
          <span class="t-eyebrow">权限</span>
          <h2 class="settings-card__title">超级管理员</h2>
          <p class="t-body-sm settings-card__lede">
            可绕过权限校验的平台运营账号。无法移除自己的超管身份。
          </p>
        </div>
        <div class="add-superuser">
          <el-input
            v-model="superuserIdentifier"
            clearable
            placeholder="用户名或邮箱"
            style="width: 220px"
            @keyup.enter="handleAddSuperuser"
          />
          <el-button type="primary" :loading="addingSuperuser" @click="handleAddSuperuser">
            添加
          </el-button>
        </div>
      </header>

      <el-table :data="superusers" stripe v-loading="superusersLoading" data-density="compact">
        <el-table-column prop="username" label="用户名" min-width="140" />
        <el-table-column prop="email" label="邮箱" min-width="200">
          <template #default="{ row }"><span class="t-mono">{{ row.email }}</span></template>
        </el-table-column>
        <el-table-column label="加入租户" min-width="240">
          <template #default="{ row }">
            <span
              v-for="m in row.memberships"
              :key="m.id"
              class="status-pill status-pill--inline"
              data-tone="neutral"
            >
              {{ m.tenant_name }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="110" fixed="right">
          <template #default="{ row }">
            <el-button
              text
              type="danger"
              size="small"
              :disabled="row.id === authStore.user?.id"
              @click="handleRemoveSuperuser(row)"
            >
              移除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '../stores/auth'
import {
  addSuperuser,
  listSuperusers,
  listTenants,
  listSystemSettings,
  removeSuperuser,
  updateSystemSettings,
} from '../api/superadmin'

const DEFAULT_REGISTRATION_TENANT_KEY = 'public.default_registration_tenant_slug'

const authStore = useAuthStore()
const loading = ref(false)
const saving = ref(false)
const tenants = ref([])
const superusers = ref([])
const superusersLoading = ref(false)
const addingSuperuser = ref(false)
const superuserIdentifier = ref('')
const form = reactive({
  defaultRegistrationTenantSlug: '',
})

const activeTenants = computed(() => tenants.value.filter((t) => t.is_active))

async function fetchData() {
  loading.value = true
  try {
    const [settingsResp, tenantsResp] = await Promise.all([
      listSystemSettings(),
      listTenants(),
    ])
    tenants.value = tenantsResp.data.data || []
    const settings = settingsResp.data.data || []
    const defaultTenant = settings.find((s) => s.key === DEFAULT_REGISTRATION_TENANT_KEY)
    form.defaultRegistrationTenantSlug = defaultTenant?.value || 'guest'
  } catch (err) {
    ElMessage.error(err.response?.data?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

async function saveSettings() {
  if (!form.defaultRegistrationTenantSlug) {
    ElMessage.warning('请选择默认注册租户')
    return
  }
  saving.value = true
  try {
    await updateSystemSettings({
      [DEFAULT_REGISTRATION_TENANT_KEY]: form.defaultRegistrationTenantSlug,
    })
    ElMessage.success('已保存')
  } catch (err) {
    ElMessage.error(err.response?.data?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function fetchSuperusers() {
  superusersLoading.value = true
  try {
    const { data } = await listSuperusers()
    superusers.value = data.data || []
  } catch (err) {
    ElMessage.error(err.response?.data?.message || '加载超级管理员失败')
  } finally {
    superusersLoading.value = false
  }
}

async function handleAddSuperuser() {
  const identifier = superuserIdentifier.value.trim()
  if (!identifier) {
    ElMessage.warning('请输入用户名或邮箱')
    return
  }
  addingSuperuser.value = true
  try {
    await addSuperuser(identifier)
    superuserIdentifier.value = ''
    ElMessage.success('已添加')
    fetchSuperusers()
  } catch (err) {
    ElMessage.error(err.response?.data?.message || '添加失败')
  } finally {
    addingSuperuser.value = false
  }
}

async function handleRemoveSuperuser(row) {
  try {
    await ElMessageBox.confirm(
      `确定移除「${row.username}」的超级管理员权限吗？`,
      '移除超级管理员',
      { type: 'warning', confirmButtonText: '移除', cancelButtonText: '取消' },
    )
    await removeSuperuser(row.id)
    ElMessage.success('已移除')
    fetchSuperusers()
  } catch (err) {
    if (err === 'cancel') return
    ElMessage.error(err.response?.data?.message || '移除失败')
  }
}

onMounted(() => {
  fetchData()
  fetchSuperusers()
})
</script>

<style scoped>
.system-settings {
  display: flex;
  flex-direction: column;
  gap: var(--space-9);
  max-width: 960px;
}

.settings-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: var(--space-8);
  display: flex;
  flex-direction: column;
  gap: var(--space-7);
  box-shadow: var(--shadow-xs);
}
.settings-card__header {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.settings-card__header--row {
  flex-direction: row;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-7);
}
.settings-card__title {
  margin: 0;
  font-size: var(--text-2xl);
  font-weight: var(--weight-bold);
  color: var(--fg-primary);
  letter-spacing: -0.01em;
}
.settings-card__lede {
  margin: 0;
  color: var(--fg-secondary);
  max-width: 56ch;
}
.settings-form { max-width: 560px; }

.add-superuser {
  display: flex;
  align-items: center;
  gap: var(--space-5);
  flex-shrink: 0;
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
.status-pill--inline {
  margin-right: var(--space-3);
  margin-bottom: var(--space-2);
}

@media (max-width: 768px) {
  .settings-card__header--row {
    flex-direction: column;
    align-items: flex-start;
  }
  .add-superuser { width: 100%; }
  .add-superuser .el-input { flex: 1; }
}
</style>
