<template>
  <div class="system-settings">
    <div class="top-bar">
      <div class="page-title">
        <el-icon class="page-icon"><Operation /></el-icon>
        <h2>系统设置</h2>
      </div>
    </div>

    <el-card shadow="never" class="settings-card" v-loading="loading">
      <template #header>
        <div class="card-title">
          <el-icon><UserFilled /></el-icon>
          <span>注册策略</span>
        </div>
      </template>

      <el-form label-width="140px" class="settings-form">
        <el-form-item label="默认注册租户">
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
    </el-card>

    <el-card shadow="never" class="settings-card">
      <template #header>
        <div class="section-head">
          <div class="card-title">
            <el-icon><User /></el-icon>
            <span>超级管理员</span>
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
        </div>
      </template>

      <el-table :data="superusers" stripe v-loading="superusersLoading">
        <el-table-column prop="username" label="用户名" min-width="140" />
        <el-table-column prop="email" label="邮箱" min-width="200" />
        <el-table-column label="加入租户" min-width="220">
          <template #default="{ row }">
            <el-tag
              v-for="m in row.memberships"
              :key="m.id"
              size="small"
              effect="plain"
              class="tenant-tag"
            >
              {{ m.tenant_name }}
            </el-tag>
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
    </el-card>
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
.system-settings { max-width: 900px; margin: 0 auto; }
.top-bar { margin-bottom: 24px; }
.page-title { display: flex; align-items: center; gap: 10px; }
.page-title h2 { margin: 0; font-weight: 600; color: var(--el-text-color-primary); }
.page-icon { font-size: 22px; color: var(--taiji-accent); }
.settings-card {
  border: 1px solid var(--el-border-color-lighter);
  margin-bottom: 20px;
}
.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 500;
  color: var(--el-text-color-primary);
}
.settings-form {
  max-width: 560px;
}
.add-superuser {
  display: flex;
  align-items: center;
  gap: 8px;
}
.tenant-tag {
  margin-right: 6px;
  margin-bottom: 4px;
}
@media (max-width: 640px) {
  .section-head {
    align-items: flex-start;
    flex-direction: column;
  }
  .add-superuser {
    width: 100%;
  }
  .add-superuser .el-input {
    flex: 1;
  }
  .settings-form :deep(.el-form-item__label) {
    width: 100% !important;
    justify-content: flex-start;
  }
  .settings-form :deep(.el-form-item__content) {
    margin-left: 0 !important;
  }
}
</style>
