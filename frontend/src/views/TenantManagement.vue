<template>
  <div class="page-shell tenant-management">
    <header class="page-header">
      <span class="page-header__eyebrow t-eyebrow">超级管理员 · 租户</span>
      <div class="page-header__row">
        <h1 class="page-header__title">租户管理</h1>
        <el-button type="primary" @click="openCreateDialog">
          <el-icon><Plus /></el-icon>&nbsp;新建租户
        </el-button>
      </div>
      <p class="page-header__lede">
        管理平台所有租户。只能切换到自己已加入并启用的租户；系统租户不可删除。
      </p>
    </header>

    <section class="data-section" data-density="compact">
      <el-table :data="tenants" stripe v-loading="loading" class="data-table">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column label="标识 (slug)" min-width="180">
          <template #default="{ row }">
            <span class="slug t-mono">{{ row.slug }}</span>
            <span v-if="row.is_system" class="status-pill status-pill--inline" data-tone="neutral">系统</span>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="名称" min-width="160" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <span class="status-pill" :data-tone="row.is_active ? 'success' : 'danger'">
              {{ row.is_active ? '正常' : '已禁用' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="用户数" width="100" align="center">
          <template #default="{ row }"><span class="t-mono">{{ row.user_count ?? '—' }}</span></template>
        </el-table-column>
        <el-table-column label="任务数" width="100" align="center">
          <template #default="{ row }"><span class="t-mono">{{ row.task_count ?? '—' }}</span></template>
        </el-table-column>
        <el-table-column label="创建时间" width="180">
          <template #default="{ row }"><span class="t-mono">{{ formatTime(row.created_at) }}</span></template>
        </el-table-column>
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="handleSwitchTo(row)"
                       :disabled="row.id === authStore.currentTenant?.id || !canSwitchTo(row)">
              切换
            </el-button>
            <el-button text type="primary" size="small" @click="openMembersDialog(row)">成员</el-button>
            <el-button text type="primary" size="small" @click="openEditDialog(row)">编辑</el-button>
            <el-button text type="danger" size="small" @click="handleDelete(row)" :disabled="row.is_system">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <el-dialog v-model="dialogVisible" :title="editMode ? '编辑租户' : '新建租户'"
               width="480px" :close-on-click-modal="false">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="标识 (slug)" prop="slug">
          <el-input
            v-model="form.slug"
            :disabled="editMode"
            placeholder="如 acme-corp（仅小写字母 / 数字 / 连字符）"
          />
          <div class="form-hint" v-if="editMode">slug 创建后不可修改</div>
        </el-form-item>
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="如 ACME 公司" />
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

    <el-dialog
      v-model="membersDialogVisible"
      :title="`成员管理 — ${memberTenant?.name || ''}`"
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
        <el-button type="primary" :loading="addingMember" @click="handleAddMember">添加</el-button>
      </div>

      <el-table :data="members" stripe v-loading="membersLoading" data-density="compact">
        <el-table-column prop="username" label="用户名" min-width="130" />
        <el-table-column prop="email" label="邮箱" min-width="200">
          <template #default="{ row }"><span class="t-mono">{{ row.email }}</span></template>
        </el-table-column>
        <el-table-column label="角色" width="140">
          <template #default="{ row }">
            <span class="status-pill" data-tone="neutral">{{ row.role_name || row.role }}</span>
          </template>
        </el-table-column>
        <el-table-column label="超级管理员" width="120">
          <template #default="{ row }">
            <span v-if="row.is_superuser" class="status-pill" data-tone="danger">是</span>
            <span v-else class="t-caption">—</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <span class="status-pill" :data-tone="row.membership_active ? 'success' : 'danger'">
              {{ row.membership_active ? '正常' : '禁用' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button text type="danger" size="small" @click="handleRemoveMember(row)">移除</el-button>
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

async function fetchRoles(tenantId = null) {
  try {
    const { data } = await listSuperadminRoles(tenantId)
    roleOptions.value = data.data || []
  } catch (err) {
    ElMessage.error(err.response?.data?.message || '加载角色失败')
  }
}

function resetForm() {
  form.slug = ''
  form.name = ''
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
  form.is_active = row.is_active
  dialogVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    if (editMode.value) {
      const payload = { name: form.name, is_active: form.is_active }
      await updateTenant(editTenantId.value, payload)
      ElMessage.success('已保存')
    } else {
      await createTenant({ slug: form.slug, name: form.name })
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
  await Promise.all([fetchMembers(), fetchRoles(row.id)])
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
.tenant-management {
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
.data-section { display: flex; flex-direction: column; gap: var(--space-6); }
.data-table {
  width: 100%;
  border-radius: var(--radius-lg);
  overflow: hidden;
  border: 1px solid var(--border-subtle);
}

.slug { color: var(--fg-primary); }

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
.status-pill[data-tone='neutral'] {
  background: var(--badge-bg-neutral);
  color: var(--badge-fg-neutral);
}
.status-pill--inline { margin-left: var(--space-5); }

.member-add {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) 160px auto;
  gap: var(--space-5);
  margin-bottom: var(--space-7);
}
.form-hint {
  font-size: var(--text-xs);
  color: var(--fg-tertiary);
  margin-top: var(--space-2);
}

@media (max-width: 900px) {
  .member-add { grid-template-columns: 1fr; }
}
@media (max-width: 768px) {
  .page-header__row { flex-direction: column; align-items: flex-start; }
}
</style>
