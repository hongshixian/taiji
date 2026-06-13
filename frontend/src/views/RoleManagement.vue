<template>
  <div class="page-shell role-management">
    <header class="page-header">
      <span class="page-header__eyebrow t-eyebrow">权限 · 角色</span>
      <div class="page-header__row">
        <h1 class="page-header__title">角色管理</h1>
        <el-button type="primary" @click="openCreateDialog" v-if="has('role:write')">
          <el-icon><Plus /></el-icon>&nbsp;新建角色
        </el-button>
      </div>
      <p class="page-header__lede">
        系统角色（admin / user / guest）由代码定义，全租户共享且不可编辑。当前租户也可以创建只对本租户生效的自定义角色。
      </p>
    </header>

    <section class="data-section" data-density="compact">
      <el-table :data="roles" stripe v-loading="loading" class="data-table">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column label="角色名" min-width="180">
          <template #default="{ row }">
            <span class="role-name">{{ row.name }}</span>
            <span v-if="row.is_system" class="status-pill status-pill--inline" data-tone="neutral">系统</span>
            <span v-else class="status-pill status-pill--inline" data-tone="progress">当前租户</span>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="220" />
        <el-table-column label="权限数" width="120">
          <template #default="{ row }">
            <span class="t-mono">{{ row.permissions.length }} 项</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="openEditDialog(row)"
                       v-if="has('role:write') && !row.is_system">
              编辑
            </el-button>
            <el-button text type="danger" size="small" @click="handleDelete(row)"
                       v-if="has('role:delete') && !row.is_system">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <el-dialog v-model="dialogVisible" :title="editMode ? '编辑角色' : '新建角色'"
               width="600px" :close-on-click-modal="false">
      <el-form :model="form" label-width="80px">
        <el-form-item label="角色名" required>
          <el-input v-model="form.name" :disabled="editMode && form.is_system"
                    placeholder="如 editor、viewer" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="权限">
          <el-checkbox-group v-model="form.permissions">
            <div v-for="(group, prefix) in groupedPermissions" :key="prefix" class="perm-group">
              <span class="t-eyebrow perm-group-title">{{ groupLabel(prefix) }}</span>
              <el-checkbox v-for="p in group" :key="p.code" :value="p.code" class="perm-item">
                <span class="perm-code">{{ p.code }}</span>
                <span class="perm-desc">{{ p.description }}</span>
              </el-checkbox>
            </div>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          {{ editMode ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listRoles, listAllPermissions, createRole, updateRole, deleteRole } from '../api/admin'
import { usePermission } from '../composables/usePermission'

const { has } = usePermission()

const roles = ref([])
const allPermissions = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const editMode = ref(false)
const editRoleId = ref(null)
const submitting = ref(false)

const form = reactive({
  name: '',
  description: '',
  permissions: [],
  is_system: false,
})

// 按前缀分组（user:/role:/task:/system:）
const groupedPermissions = computed(() => {
  const groups = {}
  allPermissions.value.forEach((p) => {
    const prefix = p.code.split(':')[0]
    if (!groups[prefix]) groups[prefix] = []
    groups[prefix].push(p)
  })
  return groups
})

function groupLabel(prefix) {
  const map = { user: '用户管理', role: '角色管理', task: '任务', system: '系统' }
  return map[prefix] || prefix
}

async function fetchData() {
  loading.value = true
  try {
    const [rolesResp, permsResp] = await Promise.all([listRoles(), listAllPermissions()])
    roles.value = rolesResp.data.data
    allPermissions.value = permsResp.data.data
  } catch (err) {
    ElMessage.error(err.response?.data?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

function resetForm() {
  form.name = ''
  form.description = ''
  form.permissions = []
  form.is_system = false
}

function openCreateDialog() {
  editMode.value = false
  editRoleId.value = null
  resetForm()
  dialogVisible.value = true
}

function openEditDialog(row) {
  editMode.value = true
  editRoleId.value = row.id
  form.name = row.name
  form.description = row.description || ''
  form.permissions = [...row.permissions]
  form.is_system = row.is_system
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!form.name.trim()) {
    ElMessage.warning('请输入角色名')
    return
  }
  submitting.value = true
  try {
    if (editMode.value) {
      const payload = { description: form.description, permissions: form.permissions }
      if (!form.is_system) payload.name = form.name
      await updateRole(editRoleId.value, payload)
      ElMessage.success('已保存')
    } else {
      await createRole({
        name: form.name,
        description: form.description,
        permissions: form.permissions,
      })
      ElMessage.success('已创建')
    }
    dialogVisible.value = false
    fetchData()
  } catch (err) {
    ElMessage.error(err.response?.data?.message || '操作失败')
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定删除角色「${row.name}」吗？如有用户绑定该角色将无法删除。`,
      '确认删除',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
    await deleteRole(row.id)
    ElMessage.success('已删除')
    fetchData()
  } catch (err) {
    if (err === 'cancel') return
    ElMessage.error(err.response?.data?.message || '删除失败')
  }
}

onMounted(fetchData)
</script>

<style scoped>
.role-management {
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

.role-name { font-weight: var(--weight-semibold); color: var(--fg-primary); }

/* 内联 status pill — 用于跟在文字后面 */
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
.status-pill[data-tone='neutral'] {
  background: var(--badge-bg-neutral);
  color: var(--badge-fg-neutral);
}
.status-pill[data-tone='progress'] {
  background: var(--color-info-bg);
  color: var(--color-info-fg);
  border-color: var(--color-info-border);
}
.status-pill--inline { margin-left: var(--space-5); }

/* 权限分组 */
.perm-group {
  width: 100%;
  margin-bottom: var(--space-7);
  padding-bottom: var(--space-5);
  border-bottom: 1px solid var(--border-subtle);
}
.perm-group:last-child { border-bottom: none; padding-bottom: 0; }
.perm-group-title {
  display: block;
  margin-bottom: var(--space-5);
  color: var(--violet-600);
  letter-spacing: 0.18em;
}
[data-theme="dark"] .perm-group-title,
html.dark .perm-group-title { color: var(--violet-300); }
.perm-item {
  display: flex !important;
  align-items: center;
  margin-right: 0 !important;
  margin-bottom: var(--space-3);
  width: 100%;
}
.perm-code {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--fg-primary);
  margin-right: var(--space-5);
  min-width: 140px;
}
.perm-desc {
  color: var(--fg-secondary);
  font-size: var(--text-sm);
}

@media (max-width: 768px) {
  .page-header__row { flex-direction: column; align-items: flex-start; }
}
</style>
