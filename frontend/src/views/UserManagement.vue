<template>
  <div class="page-shell page-shell--wide user-management">
    <header class="page-header">
      <span class="page-header__eyebrow t-eyebrow">{{ t('admin.userEyebrow') }}</span>
      <div class="page-header__row">
        <h1 class="page-header__title">{{ t('admin.userTitle') }}</h1>
        <UiButton @click="openCreateDialog">
          <template #icon><Plus class="size-4" /></template>
          {{ t('admin.userAdd') }}
        </UiButton>
      </div>
      <p class="page-header__lede">
        {{ t('admin.userLede') }}
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
            {{ memberActive(row) ? t('admin.statusNormal') : t('admin.statusDisabled') }}
          </UiBadge>
        </template>
        <template #cell-created_at="{ row }">
          <span class="t-mono">{{ formatTime(row.created_at) }}</span>
        </template>
        <template #cell-actions="{ row }">
          <div class="flex justify-end gap-1">
            <UiButton variant="text" size="sm" @click="openEditDialog(row)">{{ t('common.edit') }}</UiButton>
            <UiButton
              variant="danger-text"
              size="sm"
              :disabled="row.id === authStore.user?.id"
              @click="handleDelete(row)"
            >{{ t('admin.tenantMemberRemove') }}</UiButton>
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

    <UiDialog v-model="dialogVisible" :title="editMode ? t('admin.userDialogEdit') : t('admin.userDialogAdd')" width="480px">
      <div class="flex flex-col gap-4">
        <div v-if="editMode" class="rounded-md border border-line bg-surface-sunken px-4 py-3">
          <div class="text-sm font-semibold text-fg">{{ selectedUser?.username }}</div>
          <div class="mt-1 font-mono text-xs text-fg-secondary">{{ selectedUser?.email }}</div>
        </div>
        <UiFormItem v-else :label="t('admin.userFieldIdentifier')" required :error="errors.identifier">
          <UiInput v-model="form.identifier" :placeholder="t('admin.userPhIdentifier')" />
        </UiFormItem>
        <UiFormItem :label="t('admin.userFieldRole')" required>
          <UiSelect v-model="form.role" :options="roleSelectOptions" :placeholder="t('admin.userPhSelectRole')" />
        </UiFormItem>
        <UiFormItem v-if="editMode" :label="t('admin.userFieldMemberStatus')">
          <div class="flex items-center gap-2">
            <UiSwitch v-model="form.is_active" />
            <span class="text-sm text-fg-secondary">{{ form.is_active ? t('admin.statusNormal') : t('admin.statusDisabled') }}</span>
          </div>
        </UiFormItem>
      </div>
      <template #footer>
        <UiButton variant="secondary" @click="dialogVisible = false">{{ t('common.cancel') }}</UiButton>
        <UiButton :loading="submitting" @click="handleSubmit">
          {{ editMode ? t('common.save') : t('common.create') }}
        </UiButton>
      </template>
    </UiDialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Plus } from 'lucide-vue-next'
import { toast } from '@/lib/toast'
import { confirm } from '@/lib/confirm'
import { useAuthStore } from '@/stores/auth'
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

const { t } = useI18n()
const authStore = useAuthStore()

const columns = computed<TableColumn[]>(() => [
  { key: 'id', label: 'ID', width: 60 },
  { key: 'username', label: t('admin.colUsername'), minWidth: 120 },
  { key: 'email', label: t('admin.colEmail'), minWidth: 200 },
  { key: 'role', label: t('admin.colRole'), width: 140 },
  { key: 'status', label: t('common.status'), width: 100 },
  { key: 'created_at', label: t('common.createdAt'), width: 180 },
  { key: 'actions', label: t('common.actions'), width: 160, align: 'right', fixed: 'right' },
])

const users = ref<UserRow[]>([])
const roleOptions = ref<RoleOption[]>([])
const loading = ref(false)
const page = ref(1)
const perPage = 20
const total = ref(0)

const dialogVisible = ref(false)
const editMode = ref(false)
const editUserId = ref<number | null>(null)
const selectedUser = ref<UserRow | null>(null)
const submitting = ref(false)

const form = reactive({
  identifier: '',
  role: 'member' as string,
  is_active: true,
})
const errors = reactive({ identifier: '' })

const roleSelectOptions = computed<SelectOption[]>(() =>
  roleOptions.value.map((r) => ({ label: r.description || r.name, value: r.name, badge: r.name })),
)

function formatTime(iso?: unknown) {
  return iso ? new Date(iso as string).toLocaleString('zh-CN') : ''
}

function roleLabel(row: Record<string, unknown>) {
  const r = row as UserRow
  const role = r.role_name || r.role
  const map: Record<string, string> = {
    tenant_admin: t('admin.roleAdmin'),
    member: t('admin.roleUser'),
  }
  return (role && map[role]) || role || t('admin.roleUnknown')
}

function roleTone(row: Record<string, unknown>): 'danger' | 'neutral' | 'info' {
  const value = row as UserRow
  const role = value.role_name || value.role
  if (role === 'tenant_admin') return 'danger'
  return 'neutral'
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
      toast.error(t('admin.userNeedAdmin'))
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
      { name: 'member', description: t('admin.roleUser') },
      { name: 'tenant_admin', description: t('admin.roleAdmin') },
    ]
  }
}

function resetForm() {
  form.identifier = ''
  form.role = 'member'
  form.is_active = true
  errors.identifier = ''
}

function validate(): boolean {
  errors.identifier = !editMode.value && !form.identifier.trim()
    ? t('admin.tenantValMemberIdentifierRequired')
    : ''
  return !errors.identifier
}

function openCreateDialog() {
  editMode.value = false
  editUserId.value = null
  selectedUser.value = null
  resetForm()
  dialogVisible.value = true
}

function openEditDialog(row: Record<string, unknown>) {
  const r = row as UserRow
  editMode.value = true
  editUserId.value = r.id
  selectedUser.value = r
  form.identifier = ''
  form.role = r.role ?? 'member'
  form.is_active = r.membership_active ?? r.is_active ?? true
  errors.identifier = ''
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!validate()) return

  submitting.value = true
  try {
    if (editMode.value) {
      const payload: Record<string, unknown> = {
        role: form.role,
        membership_active: form.is_active,
      }
      await updateUser(editUserId.value as number, payload)
      toast.success(t('admin.toastUpdated'))
    } else {
      await createUser({
        identifier: form.identifier.trim(),
        role: form.role,
      })
      toast.success(t('admin.toastCreated'))
    }
    dialogVisible.value = false
    fetchUsers()
  } catch (err: unknown) {
    const e = err as { response?: { data?: { message?: string } } }
    toast.error(e.response?.data?.message || t('common.operationFailed'))
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row: Record<string, unknown>) {
  const r = row as UserRow
  const ok = await confirm({
    title: t('admin.tenantRemoveMemberTitle'),
    message: t('admin.userDeleteMsg', { name: r.username }),
    tone: 'danger',
    confirmText: t('admin.tenantMemberRemove'),
  })
  if (!ok) return
  try {
    await deleteUser(r.id)
    toast.success(t('admin.tenantMemberRemoved'))
    fetchUsers()
  } catch (err: unknown) {
    const e = err as { response?: { data?: { message?: string } } }
    toast.error(e.response?.data?.message || t('admin.deleteFailed'))
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
