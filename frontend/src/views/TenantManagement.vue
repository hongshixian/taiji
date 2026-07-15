<template>
  <div class="page-shell page-shell--wide tenant-management">
    <header class="page-header">
      <span class="page-header__eyebrow t-eyebrow">超级管理员 · 租户</span>
      <div class="page-header__row">
        <h1 class="page-header__title">租户管理</h1>
        <UiButton @click="openCreateDialog">
          <template #icon><Plus class="size-4" /></template>
          新建租户
        </UiButton>
      </div>
      <p class="page-header__lede">
        管理平台所有租户。只能切换到自己已加入并启用的租户；系统租户不可删除。
      </p>
    </header>

    <section class="data-section" data-density="compact">
      <UiTable :columns="tenantColumns" :data="tenants" row-key="id" stripe :loading="loading">
        <template #cell-slug="{ row }">
          <span class="slug t-mono">{{ row.slug }}</span>
          <UiBadge v-if="row.is_system" tone="neutral" class="ml-2">系统</UiBadge>
        </template>
        <template #cell-status="{ row }">
          <UiBadge :tone="row.is_active ? 'success' : 'danger'">
            {{ row.is_active ? '正常' : '已禁用' }}
          </UiBadge>
        </template>
        <template #cell-user_count="{ row }">
          <span class="t-mono">{{ row.user_count ?? '—' }}</span>
        </template>
        <template #cell-task_count="{ row }">
          <span class="t-mono">{{ row.task_count ?? '—' }}</span>
        </template>
        <template #cell-created_at="{ row }">
          <span class="t-mono">{{ formatTime(row.created_at) }}</span>
        </template>
        <template #cell-actions="{ row }">
          <div class="flex items-center justify-end gap-1">
            <UiButton
              variant="text"
              size="sm"
              :disabled="row.id === authStore.currentTenant?.id || !canSwitchTo(row)"
              @click="handleSwitchTo(row)"
            >
              切换
            </UiButton>
            <UiButton variant="text" size="sm" @click="openMembersDialog(row)">成员</UiButton>
            <UiDropdown>
              <template #trigger>
                <UiButton variant="text" size="sm">
                  更多<ChevronDown class="size-4" />
                </UiButton>
              </template>
              <template #default="{ close }">
                <UiDropdownItem @select="close(); openEditDialog(row)">编辑</UiDropdownItem>
                <UiDropdownItem
                  danger
                  :disabled="!!row.is_system"
                  @select="close(); handleDelete(row)"
                >
                  删除
                </UiDropdownItem>
              </template>
            </UiDropdown>
          </div>
        </template>
      </UiTable>
    </section>

    <UiDialog v-model="dialogVisible" :title="editMode ? '编辑租户' : '新建租户'" width="480px">
      <div class="flex flex-col gap-4">
        <UiFormItem label="标识 (slug)" required :error="errors.slug" :hint="editMode ? 'slug 创建后不可修改' : ''">
          <UiInput
            v-model="form.slug"
            :disabled="editMode"
            placeholder="如 acme-corp（仅小写字母 / 数字 / 连字符）"
          />
        </UiFormItem>
        <UiFormItem label="名称" required :error="errors.name">
          <UiInput v-model="form.name" placeholder="如 ACME 公司" />
        </UiFormItem>
        <UiFormItem v-if="editMode" label="状态">
          <div class="flex items-center gap-2">
            <UiSwitch v-model="form.is_active" />
            <span class="text-sm text-fg-secondary">{{ form.is_active ? '启用' : '禁用' }}</span>
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

    <UiDialog
      v-model="membersDialogVisible"
      :title="`成员管理 — ${memberTenant?.name || ''}`"
      width="900px"
    >
      <div class="member-add">
        <UiInput v-model="memberForm.identifier" placeholder="已注册用户的用户名或邮箱" />
        <UiSelect v-model="memberForm.role" :options="roleSelectOptions" placeholder="角色" />
        <UiButton :loading="addingMember" @click="handleAddMember">添加</UiButton>
      </div>

      <UiTable
        :columns="memberColumns"
        :data="members"
        row-key="id"
        stripe
        :loading="membersLoading"
      >
        <template #cell-email="{ row }">
          <span class="t-mono">{{ row.email }}</span>
        </template>
        <template #cell-role="{ row }">
          <UiBadge tone="neutral">{{ row.role_name || row.role }}</UiBadge>
        </template>
        <template #cell-superuser="{ row }">
          <UiBadge v-if="row.is_superuser" tone="danger">是</UiBadge>
          <span v-else class="t-caption">—</span>
        </template>
        <template #cell-mstatus="{ row }">
          <UiBadge :tone="row.membership_active ? 'success' : 'danger'">
            {{ row.membership_active ? '正常' : '禁用' }}
          </UiBadge>
        </template>
        <template #cell-actions="{ row }">
          <div class="flex justify-end">
            <UiButton variant="danger-text" size="sm" @click="handleRemoveMember(row)">移除</UiButton>
          </div>
        </template>
      </UiTable>
    </UiDialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { Plus, ChevronDown } from 'lucide-vue-next'
import { toast } from '@/lib/toast'
import { confirm } from '@/lib/confirm'
import { useAuthStore } from '@/stores/auth'
import {
  addTenantMember,
  createTenant,
  deleteTenant,
  listSuperadminRoles,
  listTenantMembers,
  listTenants,
  removeTenantMember,
  updateTenant,
} from '@/api/superadmin'
import UiTable, { type TableColumn } from '@/components/ui/Table.vue'
import UiButton from '@/components/ui/Button.vue'
import UiBadge from '@/components/ui/Badge.vue'
import UiDialog from '@/components/ui/Dialog.vue'
import UiFormItem from '@/components/ui/FormItem.vue'
import UiInput from '@/components/ui/Input.vue'
import UiSelect, { type SelectOption } from '@/components/ui/Select.vue'
import UiSwitch from '@/components/ui/Switch.vue'
import UiDropdown from '@/components/ui/Dropdown.vue'
import UiDropdownItem from '@/components/ui/DropdownItem.vue'

const authStore = useAuthStore()

interface TenantRow {
  id: number
  slug: string
  name: string
  is_active?: boolean
  is_system?: boolean
  user_count?: number
  task_count?: number
  created_at?: string
  [key: string]: unknown
}
interface MemberRow {
  id: number
  username: string
  email: string
  role?: string
  role_name?: string
  is_superuser?: boolean
  membership_active?: boolean
  [key: string]: unknown
}
interface RoleOption {
  name: string
  description?: string
}

const tenantColumns: TableColumn[] = [
  { key: 'id', label: 'ID', width: 60 },
  { key: 'slug', label: '标识 (slug)', minWidth: 180 },
  { key: 'name', label: '名称', minWidth: 160 },
  { key: 'status', label: '状态', width: 100 },
  { key: 'user_count', label: '用户数', width: 80, align: 'center' },
  { key: 'task_count', label: '任务数', width: 80, align: 'center' },
  { key: 'created_at', label: '创建时间', width: 160 },
  { key: 'actions', label: '操作', width: 150, align: 'right', fixed: 'right' },
]

const memberColumns: TableColumn[] = [
  { key: 'username', label: '用户名', minWidth: 130 },
  { key: 'email', label: '邮箱', minWidth: 200 },
  { key: 'role', label: '角色', width: 140 },
  { key: 'superuser', label: '超级管理员', width: 120 },
  { key: 'mstatus', label: '状态', width: 100 },
  { key: 'actions', label: '操作', width: 100, align: 'right', fixed: 'right' },
]

const tenants = ref<TenantRow[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const editMode = ref(false)
const editTenantId = ref<number | null>(null)
const submitting = ref(false)
const membersDialogVisible = ref(false)
const memberTenant = ref<TenantRow | null>(null)
const members = ref<MemberRow[]>([])
const membersLoading = ref(false)
const addingMember = ref(false)
const roleOptions = ref<RoleOption[]>([])

const form = reactive({
  slug: '',
  name: '',
  is_active: true,
})
const memberForm = reactive({
  identifier: '',
  role: 'user' as string,
})
const errors = reactive({ slug: '', name: '' })

const roleSelectOptions = computed<SelectOption[]>(() =>
  roleOptions.value.map((r) => ({ label: r.description || r.name, value: r.name })),
)

function formatTime(iso?: unknown) {
  return iso ? new Date(iso as string).toLocaleString('zh-CN') : ''
}

function canSwitchTo(row: Record<string, unknown>) {
  const id = (row as TenantRow).id
  const memberships = ((authStore.user as { memberships?: unknown[] } | null)?.memberships ?? []) as Array<{
    tenant_id?: number
    is_active?: boolean
  }>
  return memberships.some((m) => m.tenant_id === id && m.is_active)
}

function validate(): boolean {
  errors.slug = ''
  errors.name = ''
  if (!editMode.value) {
    const slug = form.slug.trim()
    if (!slug) errors.slug = '请输入 slug'
    else if (!/^[a-z0-9-]+$/.test(slug)) errors.slug = '仅允许小写字母 / 数字 / 连字符'
    else if (slug.length < 2 || slug.length > 50) errors.slug = '长度 2-50'
  }
  const name = form.name.trim()
  if (!name) errors.name = '请输入名称'
  else if (name.length > 100) errors.name = '最多 100 字符'
  return !errors.slug && !errors.name
}

async function fetchTenants() {
  loading.value = true
  try {
    const { data } = await listTenants()
    tenants.value = data.data || []
  } catch (err: unknown) {
    const e = err as { response?: { data?: { message?: string } } }
    toast.error(e.response?.data?.message || '加载租户失败')
  } finally {
    loading.value = false
  }
}

async function fetchRoles(tenantId: number | null = null) {
  try {
    const { data } = await listSuperadminRoles(tenantId as null)
    roleOptions.value = data.data || []
  } catch (err: unknown) {
    const e = err as { response?: { data?: { message?: string } } }
    toast.error(e.response?.data?.message || '加载角色失败')
  }
}

function resetForm() {
  form.slug = ''
  form.name = ''
  form.is_active = true
  errors.slug = ''
  errors.name = ''
}

function openCreateDialog() {
  editMode.value = false
  editTenantId.value = null
  resetForm()
  dialogVisible.value = true
}

function openEditDialog(row: Record<string, unknown>) {
  const r = row as TenantRow
  editMode.value = true
  editTenantId.value = r.id
  form.slug = r.slug
  form.name = r.name
  form.is_active = r.is_active ?? true
  errors.slug = ''
  errors.name = ''
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!validate()) return

  submitting.value = true
  try {
    if (editMode.value) {
      await updateTenant(editTenantId.value, { name: form.name, is_active: form.is_active })
      toast.success('已保存')
    } else {
      await createTenant({ slug: form.slug, name: form.name })
      toast.success('已创建')
    }
    dialogVisible.value = false
    fetchTenants()
  } catch (err: unknown) {
    const e = err as { response?: { data?: { message?: string } } }
    toast.error(e.response?.data?.message || '操作失败')
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row: Record<string, unknown>) {
  const r = row as TenantRow
  if (r.is_system) {
    toast.warning('系统租户不可删除')
    return
  }
  const ok = await confirm({
    title: '确认删除',
    message: `确定删除租户「${r.name}」(${r.slug}) 吗？如租户内仍有用户或任务将无法删除。`,
    tone: 'danger',
    confirmText: '删除',
  })
  if (!ok) return
  try {
    await deleteTenant(r.id)
    toast.success('已删除')
    fetchTenants()
  } catch (err: unknown) {
    const e = err as { response?: { data?: { message?: string } } }
    toast.error(e.response?.data?.message || '删除失败')
  }
}

async function handleSwitchTo(row: Record<string, unknown>) {
  const r = row as TenantRow
  const ok = await confirm({
    title: '切换租户',
    message: `切换到租户「${r.name}」？后续操作将在该租户上下文下进行。`,
    confirmText: '切换',
  })
  if (!ok) return
  try {
    await authStore.switchTenant(r.id)
    toast.success(`已切换到「${r.name}」`)
    setTimeout(() => window.location.reload(), 300)
  } catch (err: unknown) {
    const e = err as { response?: { data?: { message?: string } } }
    toast.error(e.response?.data?.message || '切换失败')
  }
}

function resetMemberForm() {
  memberForm.identifier = ''
  memberForm.role = 'user'
}

async function openMembersDialog(row: Record<string, unknown>) {
  const r = row as TenantRow
  memberTenant.value = r
  resetMemberForm()
  membersDialogVisible.value = true
  await Promise.all([fetchMembers(), fetchRoles(r.id)])
}

async function fetchMembers() {
  if (!memberTenant.value) return
  membersLoading.value = true
  try {
    const { data } = await listTenantMembers(memberTenant.value.id)
    members.value = data.data || []
  } catch (err: unknown) {
    const e = err as { response?: { data?: { message?: string } } }
    toast.error(e.response?.data?.message || '加载成员失败')
  } finally {
    membersLoading.value = false
  }
}

async function handleAddMember() {
  if (!memberTenant.value) return
  if (!memberForm.identifier.trim()) {
    toast.warning('请输入用户名或邮箱')
    return
  }
  addingMember.value = true
  try {
    await addTenantMember(memberTenant.value.id, {
      identifier: memberForm.identifier.trim(),
      role: memberForm.role,
    })
    toast.success('已添加成员')
    resetMemberForm()
    await Promise.all([fetchMembers(), fetchTenants()])
  } catch (err: unknown) {
    const e = err as { response?: { data?: { message?: string } } }
    toast.error(e.response?.data?.message || '添加成员失败')
  } finally {
    addingMember.value = false
  }
}

async function handleRemoveMember(row: Record<string, unknown>) {
  const r = row as MemberRow
  if (!memberTenant.value) return
  const ok = await confirm({
    title: '移除成员',
    message: `确定从租户「${memberTenant.value.name}」移除成员「${r.username}」吗？`,
    tone: 'danger',
    confirmText: '移除',
  })
  if (!ok) return
  try {
    await removeTenantMember(memberTenant.value.id, r.id)
    toast.success('已移除')
    await Promise.all([fetchMembers(), fetchTenants()])
  } catch (err: unknown) {
    const e = err as { response?: { data?: { message?: string } } }
    toast.error(e.response?.data?.message || '移除失败')
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
.data-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.slug {
  color: var(--fg-primary);
}

.member-add {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) 160px auto;
  gap: var(--space-5);
  margin-bottom: var(--space-7);
}

@media (max-width: 900px) {
  .member-add {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 768px) {
  .page-header__row {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
