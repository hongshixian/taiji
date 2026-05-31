<template>
  <div class="role-management">
    <div class="top-bar">
      <div class="page-title">
        <el-icon class="page-icon"><Key /></el-icon>
        <h2>角色管理</h2>
      </div>
      <el-button type="primary" @click="openCreateDialog" v-if="has('role:write')">
        <el-icon><Plus /></el-icon>&nbsp;新建角色
      </el-button>
    </div>

    <!-- 角色列表 -->
    <el-table :data="roles" stripe v-loading="loading">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column label="角色名" min-width="120">
        <template #default="{ row }">
          <span class="role-name">{{ row.name }}</span>
          <el-tag v-if="row.is_system" size="small" type="info" class="system-tag">系统</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="描述" min-width="200" />
      <el-table-column label="权限数" width="100">
        <template #default="{ row }">
          <el-tag size="small">{{ row.permissions.length }} 项</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button text type="primary" size="small" @click="openEditDialog(row)" v-if="has('role:write')">
            编辑
          </el-button>
          <el-button text type="danger" size="small" @click="handleDelete(row)"
                     v-if="has('role:delete') && !row.is_system">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 创建/编辑弹窗 -->
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
              <div class="perm-group-title">{{ groupLabel(prefix) }}</div>
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
.role-management { max-width: 1200px; margin: 0 auto; }
.top-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.page-title { display: flex; align-items: center; gap: 10px; }
.page-title h2 { margin: 0; font-weight: 600; color: var(--el-text-color-primary); }
.page-icon { font-size: 22px; color: var(--taiji-accent); }

.role-name { font-weight: 500; color: var(--el-text-color-primary); }
.system-tag { margin-left: 8px; }

.perm-group { width: 100%; margin-bottom: 16px; }
.perm-group-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--taiji-accent);
  margin-bottom: 8px;
  letter-spacing: 1px;
}
.perm-item {
  display: flex !important;
  align-items: center;
  margin-right: 0 !important;
  margin-bottom: 6px;
  width: 100%;
}
.perm-code {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
  color: var(--el-text-color-regular);
  margin-right: 12px;
  min-width: 130px;
}
.perm-desc {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
</style>
