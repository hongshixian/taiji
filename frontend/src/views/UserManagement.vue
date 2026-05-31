<template>
  <div class="user-management">
    <div class="top-bar">
      <div class="page-title">
        <el-icon class="page-icon"><UserFilled /></el-icon>
        <h2>用户管理</h2>
      </div>
      <el-button type="primary" @click="openCreateDialog">
        <el-icon><Plus /></el-icon>&nbsp;添加用户
      </el-button>
    </div>

    <!-- 用户表格 -->
    <el-table :data="users" stripe v-loading="loading">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="username" label="用户名" min-width="120" />
      <el-table-column prop="email" label="邮箱" min-width="180" />
      <el-table-column label="角色" width="120">
        <template #default="{ row }">
          <el-tag :type="roleTagType(row)" size="small">
            {{ roleLabel(row) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="memberActive(row) ? 'success' : 'danger'" size="small">
            {{ memberActive(row) ? '正常' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="170">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button text type="primary" size="small" @click="openEditDialog(row)">编辑</el-button>
          <el-button text type="danger" size="small" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <el-pagination
      v-if="total > perPage"
      v-model:current-page="page"
      :page-size="perPage"
      :total="total"
      layout="prev, pager, next"
      class="pagination"
      @current-change="fetchUsers"
    />

    <!-- 创建/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editMode ? '编辑用户' : '添加用户'" width="480px" :close-on-click-modal="false">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" :disabled="editMode" placeholder="3-80 个字符" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="user@example.com" />
        </el-form-item>
        <el-form-item label="密码" :prop="editMode ? 'password' : 'password'">
          <el-input v-model="form.password" type="password" show-password :placeholder="editMode ? '留空则不修改' : '至少 6 位'" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="form.role" placeholder="选择角色" style="width: 100%">
            <el-option v-for="r in roleOptions" :key="r.name"
                       :label="r.description || r.name" :value="r.name">
              <span style="float: left">{{ r.description || r.name }}</span>
              <span style="float: right; color: var(--el-text-color-secondary); font-size: 12px; font-family: monospace;">{{ r.name }}</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item v-if="editMode" label="成员状态">
          <el-switch v-model="form.is_active" active-text="正常" inactive-text="禁用" />
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
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listUsers, createUser, updateUser, deleteUser, listRoles } from '../api/admin'

const users = ref([])
const roleOptions = ref([])
const loading = ref(false)
const page = ref(1)
const perPage = 20
const total = ref(0)

const dialogVisible = ref(false)
const editMode = ref(false)
const editUserId = ref(null)
const submitting = ref(false)
const formRef = ref(null)

const form = reactive({
  username: '',
  email: '',
  password: '',
  role: 'user',
  is_active: true,
})

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 80, message: '3-80 个字符', trigger: 'blur' },
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
  ],
}

function formatTime(iso) {
  return iso ? new Date(iso).toLocaleString('zh-CN') : ''
}

function roleLabel(row) {
  // 优先用 role_name (后端 RBAC)；兜底用 role 字符串映射
  if (row.role_name) return row.role_name
  return { admin: '管理员', user: '普通用户', guest: '访客' }[row.role] || row.role || '未知'
}

function roleTagType(row) {
  // 系统角色用固定颜色；自定义角色用默认色
  if (row.role === 'admin') return 'danger'
  if (row.role === 'guest') return 'info'
  if (row.role === 'user') return 'info'
  return ''  // 自定义角色 — 主色
}

function memberActive(row) {
  return row.is_active && (row.membership_active ?? true)
}

async function fetchUsers() {
  loading.value = true
  try {
    const { data } = await listUsers(page.value, perPage)
    users.value = data.data.items
    total.value = data.data.total
  } catch (err) {
    if (err.response?.status === 403) {
      ElMessage.error('需要管理员权限')
    }
  } finally {
    loading.value = false
  }
}

async function fetchRoles() {
  try {
    const { data } = await listRoles()
    roleOptions.value = data.data
  } catch {
    // 没权限或失败：回退默认两个
    roleOptions.value = [
      { name: 'user', description: '普通用户' },
      { name: 'admin', description: '管理员' },
    ]
  }
}

function resetForm() {
  form.username = ''
  form.email = ''
  form.password = ''
  form.role = 'user'
  form.is_active = true
  formRef.value?.resetFields()
}

function openCreateDialog() {
  editMode.value = false
  editUserId.value = null
  resetForm()
  dialogVisible.value = true
}

function openEditDialog(row) {
  editMode.value = true
  editUserId.value = row.id
  form.username = row.username
  form.email = row.email
  form.password = ''
  form.role = row.role
  form.is_active = row.membership_active ?? row.is_active
  dialogVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    if (editMode.value) {
      const payload = { email: form.email, role: form.role, membership_active: form.is_active }
      if (form.password) payload.password = form.password
      await updateUser(editUserId.value, payload)
      ElMessage.success('已更新')
    } else {
      await createUser({ username: form.username, email: form.email, password: form.password, role: form.role })
      ElMessage.success('已创建')
    }
    dialogVisible.value = false
    fetchUsers()
  } catch (err) {
    ElMessage.error(err.response?.data?.message || '操作失败')
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除用户「${row.username}」吗？此操作不可恢复。`, '确认删除', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
    await deleteUser(row.id)
    ElMessage.success('已删除')
    fetchUsers()
  } catch {
    // 取消
  }
}

onMounted(() => {
  fetchUsers()
  fetchRoles()
})
</script>

<style scoped>
.user-management { max-width: 1200px; margin: 0 auto; }
.top-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.page-title { display: flex; align-items: center; gap: 10px; }
.page-title h2 { margin: 0; font-weight: 600; color: var(--el-text-color-primary); }
.page-icon { font-size: 22px; color: var(--taiji-accent); }
.pagination { margin-top: 16px; justify-content: center; }
</style>
