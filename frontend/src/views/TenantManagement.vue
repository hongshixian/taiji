<template>
  <div class="tenant-management">
    <div class="top-bar">
      <div class="page-title">
        <el-icon class="page-icon"><OfficeBuilding /></el-icon>
        <h2>租户管理</h2>
      </div>
      <el-button type="primary" @click="openCreateDialog">
        <el-icon><Plus /></el-icon>&nbsp;新建租户
      </el-button>
    </div>

    <el-alert
      v-if="authStore.isSuperuser"
      type="info"
      :closable="false"
      show-icon
      style="margin-bottom: 16px;"
    >
      作为超级管理员，你可以管理平台所有租户；只有已加入的租户可切换为当前操作租户。
    </el-alert>

    <!-- 租户表格 -->
    <el-table :data="tenants" stripe v-loading="loading">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column label="标识 (slug)" min-width="140">
        <template #default="{ row }">
          <span class="slug">{{ row.slug }}</span>
          <el-tag v-if="row.is_system" size="small" type="info" class="system-tag">系统</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="name" label="名称" min-width="140" />
      <el-table-column label="套餐" width="110">
        <template #default="{ row }">
          <el-tag :type="planTagType(row.plan)" size="small" effect="plain">{{ row.plan }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
            {{ row.is_active ? '正常' : '已禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="用户数" width="90" align="center">
        <template #default="{ row }">{{ row.user_count ?? '-' }}</template>
      </el-table-column>
      <el-table-column label="任务数" width="90" align="center">
        <template #default="{ row }">{{ row.task_count ?? '-' }}</template>
      </el-table-column>
      <el-table-column label="创建时间" width="170">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="250" fixed="right">
        <template #default="{ row }">
          <el-button text type="primary" size="small" @click="handleSwitchTo(row)"
                     :disabled="row.id === authStore.currentTenant?.id || !canSwitchTo(row)">
            切换
          </el-button>
          <el-button text type="primary" size="small" @click="openMembersDialog(row)">
            成员
          </el-button>
          <el-button text type="primary" size="small" @click="openEditDialog(row)">
            编辑
          </el-button>
          <el-button text type="danger" size="small" @click="handleDelete(row)"
                     :disabled="row.is_system">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 创建/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editMode ? '编辑租户' : '新建租户'"
               width="480px" :close-on-click-modal="false">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="标识 (slug)" prop="slug">
          <el-input
            v-model="form.slug"
            :disabled="editMode"
            placeholder="如 acme-corp（仅小写字母/数字/连字符）"
          />
          <div class="form-hint" v-if="editMode">slug 创建后不可修改</div>
        </el-form-item>
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="如 ACME 公司" />
        </el-form-item>
        <el-form-item label="套餐" prop="plan">
          <el-select v-model="form.plan" style="width: 100%">
            <el-option label="Free 免费版" value="free" />
            <el-option label="Pro 专业版" value="pro" />
            <el-option label="Enterprise 企业版" value="enterprise" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="editMode" label="状态">
          <el-switch v-model="form.is_active" active-text="启用" inactive-text="禁用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          {{ editMode ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 成员管理弹窗 -->
    <el-dialog
      v-model="membersDialogVisible"
      :title="`成员管理 - ${memberTenant?.name || ''}`"
      width="760px"
      :close-on-click-modal="false"
    >
      <div class="member-add">
        <el-input v-model="memberForm.identifier" placeholder="已注册用户的用户名或邮箱" />
        <el-select v-model="memberForm.role" placeholder="角色">
          <el-option
            v-for="role in roleOptions"
            :key="role.name"
            :label="role.description || role.name"
            :value="role.name"
          />
        </el-select>
        <el-button type="primary" :loading="addingMember" @click="handleAddMember">
          添加
        </el-button>
      </div>

      <el-table :data="members" stripe v-loading="membersLoading">
        <el-table-column prop="username" label="用户名" min-width="130" />
        <el-table-column prop="email" label="邮箱" min-width="180" />
        <el-table-column label="角色" width="130">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ row.role_name || row.role }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="超级管理员" width="110">
          <template #default="{ row }">
            <el-tag v-if="row.is_superuser" type="danger" size="small">是</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.membership_active ? 'success' : 'danger'" size="small">
              {{ row.membership_active ? '正常' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button text type="danger" size="small" @click="handleRemoveMember(row)">
              移除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '../stores/auth'
import {
  addTenantMember,
  createTenant,
  deleteTenant,
  listSuperadminRoles,
  listTenantMembers,
  listTenants,
  removeTenantMember,
  updateTenant,
} from '../api/superadmin'

const authStore = useAuthStore()

const tenants = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const editMode = ref(false)
const editTenantId = ref(null)
const submitting = ref(false)
const formRef = ref(null)
const membersDialogVisible = ref(false)
const memberTenant = ref(null)
const members = ref([])
const membersLoading = ref(false)
const addingMember = ref(false)
const roleOptions = ref([])

const form = reactive({
  slug: '',
  name: '',
  plan: 'free',
  is_active: true,
})
const memberForm = reactive({
  identifier: '',
  role: 'user',
})

const rules = {
  slug: [
    { required: true, message: '请输入 slug', trigger: 'blur' },
    { pattern: /^[a-z0-9-]+$/, message: '仅允许小写字母 / 数字 / 连字符', trigger: 'blur' },
    { min: 2, max: 50, message: '长度 2-50', trigger: 'blur' },
  ],
  name: [
    { required: true, message: '请输入名称', trigger: 'blur' },
    { max: 100, message: '最多 100 字符', trigger: 'blur' },
  ],
}

function formatTime(iso) {
  return iso ? new Date(iso).toLocaleString('zh-CN') : ''
}

function planTagType(plan) {
  return { free: 'info', pro: 'warning', enterprise: 'danger' }[plan] || 'info'
}

function canSwitchTo(row) {
  return (authStore.user?.memberships || []).some((m) => m.tenant_id === row.id && m.is_active)
}

async function fetchTenants() {
  loading.value = true
  try {
    const { data } = await listTenants()
    tenants.value = data.data || []
  } catch (err) {
    ElMessage.error(err.response?.data?.message || '加载租户失败')
  } finally {
    loading.value = false
  }
}

async function fetchRoles() {
  try {
    const { data } = await listSuperadminRoles()
    roleOptions.value = data.data || []
  } catch (err) {
    ElMessage.error(err.response?.data?.message || '加载角色失败')
  }
}

function resetForm() {
  form.slug = ''
  form.name = ''
  form.plan = 'free'
  form.is_active = true
  formRef.value?.resetFields()
}

function openCreateDialog() {
  editMode.value = false
  editTenantId.value = null
  resetForm()
  dialogVisible.value = true
}

function openEditDialog(row) {
  editMode.value = true
  editTenantId.value = row.id
  form.slug = row.slug
  form.name = row.name
  form.plan = row.plan
  form.is_active = row.is_active
  dialogVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    if (editMode.value) {
      const payload = { name: form.name, plan: form.plan, is_active: form.is_active }
      await updateTenant(editTenantId.value, payload)
      ElMessage.success('已保存')
    } else {
      await createTenant({ slug: form.slug, name: form.name, plan: form.plan })
      ElMessage.success('已创建')
    }
    dialogVisible.value = false
    fetchTenants()
  } catch (err) {
    ElMessage.error(err.response?.data?.message || '操作失败')
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row) {
  if (row.is_system) {
    ElMessage.warning('系统租户不可删除')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确定删除租户「${row.name}」(${row.slug}) 吗？如租户内仍有用户或任务将无法删除。`,
      '确认删除',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
    await deleteTenant(row.id)
    ElMessage.success('已删除')
    fetchTenants()
  } catch (err) {
    if (err === 'cancel') return
    ElMessage.error(err.response?.data?.message || '删除失败')
  }
}

async function handleSwitchTo(row) {
  try {
    await ElMessageBox.confirm(
      `切换到租户「${row.name}」？后续操作将在该租户上下文下进行。`,
      '切换租户',
      { type: 'info', confirmButtonText: '切换', cancelButtonText: '取消' },
    )
    await authStore.switchTenant(row.id)
    ElMessage.success(`已切换到「${row.name}」`)
    setTimeout(() => window.location.reload(), 300)
  } catch (err) {
    if (err === 'cancel') return
    ElMessage.error(err.response?.data?.message || '切换失败')
  }
}

function resetMemberForm() {
  memberForm.identifier = ''
  memberForm.role = 'user'
}

async function openMembersDialog(row) {
  memberTenant.value = row
  resetMemberForm()
  membersDialogVisible.value = true
  await fetchMembers()
}

async function fetchMembers() {
  if (!memberTenant.value) return
  membersLoading.value = true
  try {
    const { data } = await listTenantMembers(memberTenant.value.id)
    members.value = data.data || []
  } catch (err) {
    ElMessage.error(err.response?.data?.message || '加载成员失败')
  } finally {
    membersLoading.value = false
  }
}

async function handleAddMember() {
  if (!memberTenant.value) return
  if (!memberForm.identifier.trim()) {
    ElMessage.warning('请输入用户名或邮箱')
    return
  }
  addingMember.value = true
  try {
    await addTenantMember(memberTenant.value.id, {
      identifier: memberForm.identifier.trim(),
      role: memberForm.role,
    })
    ElMessage.success('已添加成员')
    resetMemberForm()
    await Promise.all([fetchMembers(), fetchTenants()])
  } catch (err) {
    ElMessage.error(err.response?.data?.message || '添加成员失败')
  } finally {
    addingMember.value = false
  }
}

async function handleRemoveMember(row) {
  if (!memberTenant.value) return
  try {
    await ElMessageBox.confirm(
      `确定从租户「${memberTenant.value.name}」移除成员「${row.username}」吗？`,
      '移除成员',
      { type: 'warning', confirmButtonText: '移除', cancelButtonText: '取消' },
    )
    await removeTenantMember(memberTenant.value.id, row.id)
    ElMessage.success('已移除')
    await Promise.all([fetchMembers(), fetchTenants()])
  } catch (err) {
    if (err === 'cancel') return
    ElMessage.error(err.response?.data?.message || '移除失败')
  }
}

onMounted(() => {
  fetchTenants()
  fetchRoles()
})
</script>

<style scoped>
.tenant-management { max-width: 1200px; margin: 0 auto; }
.top-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.page-title { display: flex; align-items: center; gap: 10px; }
.page-title h2 { margin: 0; font-weight: 600; color: var(--el-text-color-primary); }
.page-icon { font-size: 22px; color: var(--taiji-accent); }

.slug {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 13px;
  color: var(--el-text-color-primary);
}
.system-tag { margin-left: 8px; }
.member-add {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) 150px auto;
  gap: 8px;
  margin-bottom: 16px;
}
.form-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}
@media (max-width: 900px) {
  .member-add {
    grid-template-columns: 1fr;
  }
}
</style>
