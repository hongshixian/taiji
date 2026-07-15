<template>
  <div class="page-shell page-shell--wide user-management">
    <header class="page-header">
      <span class="page-header__eyebrow t-eyebrow">租户 · 成员</span>
      <div class="page-header__row">
        <h1 class="page-header__title">用户管理</h1>
        <UiButton @click="openCreateDialog">
          <template #icon><Plus class="size-4" /></template>
          添加用户
        </UiButton>
      </div>
      <p class="page-header__lede">
        管理当前租户的成员、角色与状态。删除会移除该成员资格；若用户没有其他租户身份，全局账号也会被删除。
      </p>
    </header>

    <section class="data-section" data-density="compact">
      <UiTable :columns="columns" :data="users" row-key="id" stripe :loading="loading">
        <template #cell-email="{ row }">
          <span class="t-mono">{{ row.email }}</span>
        </template>
        <template #cell-role="{ row }">
          <UiBadge :tone="roleTone(row)">{{ roleLabel(row) }}</UiBadge>
        </template>
        <template #cell-status="{ row }">
          <UiBadge :tone="memberActive(row) ? 'success' : 'danger'">
            {{ memberActive(row) ? '正常' : '禁用' }}
          </UiBadge>
        </template>
        <template #cell-created_at="{ row }">
          <span class="t-mono">{{ formatTime(row.created_at) }}</span>
        </template>
        <template #cell-actions="{ row }">
          <div class="flex justify-end gap-1">
            <UiButton variant="text" size="sm" @click="openEditDialog(row)">编辑</UiButton>
            <UiButton variant="danger-text" size="sm" @click="handleDelete(row)">删除</UiButton>
          </div>
        </template>
      </UiTable>

      <UiPagination
        v-if="total > perPage"
        :current-page="page"
        :page-size="perPage"
        :total="total"
        class="pagination"
        @current-change="handlePageChange"
      />
    </section>

    <UiDialog v-model="dialogVisible" :title="editMode ? '编辑用户' : '添加用户'" width="480px">
      <div class="flex flex-col gap-4">
        <UiFormItem label="用户名" required :error="errors.username">
          <UiInput v-model="form.username" :disabled="editMode" placeholder="3 至 80 个字符" />
        </UiFormItem>
        <UiFormItem label="邮箱" required :error="errors.email">
          <UiInput v-model="form.email" placeholder="user@example.com" />
        </UiFormItem>
        <UiFormItem label="密码">
          <UiInput
            v-model="form.password"
            type="password"
            :placeholder="editMode ? '留空则不修改' : '至少 6 位'"
          />
        </UiFormItem>
        <UiFormItem label="角色" required>
          <UiSelect v-model="form.role" :options="roleSelectOptions" placeholder="选择角色" />
        </UiFormItem>
        <UiFormItem v-if="editMode" label="成员状态">
          <div class="flex items-center gap-2">
            <UiSwitch v-model="form.is_active" />
            <span class="text-sm text-fg-secondary">{{ form.is_active ? '正常' : '禁用' }}</span>
          </div>
        </UiFormItem>
      </div>
      <template #footer>
        <UiButton variant="secondary" @click="dialogVisible = false">取消</UiButton>
        <UiButton :loading="submitting" @click="handleSubmit">
          {{ editMode ? '保存' : '创建' }}
        </UiButton>
      </template>
    </UiDialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { Plus } from 'lucide-vue-next'
import { toast } from '@/lib/toast'
import { confirm } from '@/lib/confirm'
import { listUsers, createUser, updateUser, deleteUser, listRoles } from '@/api/admin'
import UiTable, { type TableColumn } from '@/components/ui/Table.vue'
import UiButton from '@/components/ui/Button.vue'
import UiBadge from '@/components/ui/Badge.vue'
import UiPagination from '@/components/ui/Pagination.vue'
import UiDialog from '@/components/ui/Dialog.vue'
import UiFormItem from '@/components/ui/FormItem.vue'
import UiInput from '@/components/ui/Input.vue'
import UiSelect, { type SelectOption } from '@/components/ui/Select.vue'
import UiSwitch from '@/components/ui/Switch.vue'

interface UserRow {
  id: number
  username: string
  email: string
  role?: string
  role_name?: string
  is_active?: boolean
  membership_active?: boolean
  created_at?: string
  [key: string]: unknown
}
interface RoleOption {
  name: string
  description?: string
}

const columns: TableColumn[] = [
  { key: 'id', label: 'ID', width: 60 },
  { key: 'username', label: '用户名', minWidth: 120 },
  { key: 'email', label: '邮箱', minWidth: 200 },
  { key: 'role', label: '角色', width: 140 },
  { key: 'status', label: '状态', width: 100 },
  { key: 'created_at', label: '创建时间', width: 180 },
  { key: 'actions', label: '操作', width: 160, align: 'right', fixed: 'right' },
]

const users = ref<UserRow[]>([])
const roleOptions = ref<RoleOption[]>([])
const loading = ref(false)
const page = ref(1)
const perPage = 20
const total = ref(0)

const dialogVisible = ref(false)
const editMode = ref(false)
const editUserId = ref<number | null>(null)
const submitting = ref(false)

const form = reactive({
  username: '',
  email: '',
  password: '',
  role: 'user' as string,
  is_active: true,
})
const errors = reactive({ username: '', email: '' })

const roleSelectOptions = computed<SelectOption[]>(() =>
  roleOptions.value.map((r) => ({ label: r.description || r.name, value: r.name, badge: r.name })),
)

function formatTime(iso?: unknown) {
  return iso ? new Date(iso as string).toLocaleString('zh-CN') : ''
}

function roleLabel(row: Record<string, unknown>) {
  const r = row as UserRow
  // 优先用 role_name (后端 RBAC)；兜底用 role 字符串映射
  if (r.role_name) return r.role_name
  const map: Record<string, string> = { admin: '管理员', user: '普通用户', guest: '访客' }
  return (r.role && map[r.role]) || r.role || '未知'
}

function roleTone(row: Record<string, unknown>): 'danger' | 'neutral' | 'info' {
  const role = (row as UserRow).role
  if (role === 'admin') return 'danger'
  if (role === 'guest') return 'neutral'
  if (role === 'user') return 'neutral'
  return 'info' // 自定义角色 — 紫色 info
}

function memberActive(row: Record<string, unknown>) {
  const r = row as UserRow
  return !!r.is_active && (r.membership_active ?? true)
}

async function fetchUsers() {
  loading.value = true
  try {
    const { data } = await listUsers(page.value, perPage)
    users.value = data.data.items
    total.value = data.data.total
  } catch (err: unknown) {
    const e = err as { response?: { status?: number } }
    if (e.response?.status === 403) {
      toast.error('需要管理员权限')
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
  errors.username = ''
  errors.email = ''
}

function validate(): boolean {
  errors.username = ''
  errors.email = ''
  if (!editMode.value) {
    const name = form.username.trim()
    if (!name) errors.username = '请输入用户名'
    else if (name.length < 3 || name.length > 80) errors.username = '3-80 个字符'
  }
  const email = form.email.trim()
  if (!email) errors.email = '请输入邮箱'
  else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) errors.email = '邮箱格式不正确'
  return !errors.username && !errors.email
}

function openCreateDialog() {
  editMode.value = false
  editUserId.value = null
  resetForm()
  dialogVisible.value = true
}

function openEditDialog(row: Record<string, unknown>) {
  const r = row as UserRow
  editMode.value = true
  editUserId.value = r.id
  form.username = r.username
  form.email = r.email
  form.password = ''
  form.role = r.role ?? 'user'
  form.is_active = r.membership_active ?? r.is_active ?? true
  errors.username = ''
  errors.email = ''
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!validate()) return

  submitting.value = true
  try {
    if (editMode.value) {
      const payload: Record<string, unknown> = {
        email: form.email,
        role: form.role,
        membership_active: form.is_active,
      }
      if (form.password) payload.password = form.password
      await updateUser(editUserId.value as number, payload)
      toast.success('已更新')
    } else {
      await createUser({
        username: form.username,
        email: form.email,
        password: form.password,
        role: form.role,
      })
      toast.success('已创建')
    }
    dialogVisible.value = false
    fetchUsers()
  } catch (err: unknown) {
    const e = err as { response?: { data?: { message?: string } } }
    toast.error(e.response?.data?.message || '操作失败')
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row: Record<string, unknown>) {
  const r = row as UserRow
  const ok = await confirm({
    title: '确认删除',
    message: `确定删除用户「${r.username}」吗？此操作不可恢复。`,
    tone: 'danger',
    confirmText: '删除',
  })
  if (!ok) return
  try {
    await deleteUser(r.id)
    toast.success('已删除')
    fetchUsers()
  } catch (err: unknown) {
    const e = err as { response?: { data?: { message?: string } } }
    toast.error(e.response?.data?.message || '删除失败')
  }
}

function handlePageChange(p: number) {
  page.value = p
  fetchUsers()
}

onMounted(() => {
  fetchUsers()
  fetchRoles()
})
</script>

<style scoped>
.user-management {
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
.data-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}
.pagination {
  margin-top: var(--space-3);
}

@media (max-width: 768px) {
  .page-header__row {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
