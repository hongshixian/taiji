<template>
  <div class="page-shell page-shell--wide tenant-management">
    <header class="page-header">
      <span class="page-header__eyebrow t-eyebrow">{{ t('admin.tenantEyebrow') }}</span>
      <div class="page-header__row">
        <h1 class="page-header__title">{{ t('admin.tenantTitle') }}</h1>
        <UiButton @click="openCreateDialog">
          <template #icon><Plus class="size-4" /></template>
          {{ t('admin.tenantAdd') }}
        </UiButton>
      </div>
      <p class="page-header__lede">
        {{ t('admin.tenantLede') }}
      </p>
    </header>

    <section class="data-section" data-density="compact">
      <UiTable :columns="tenantColumns" :data="tenants" row-key="id" stripe :loading="loading">
        <template #cell-slug="{ row }">
          <span class="slug t-mono">{{ row.slug }}</span>
          <UiBadge v-if="row.is_system" tone="neutral" class="ml-2">{{ t('admin.badgeSystem') }}</UiBadge>
        </template>
        <template #cell-status="{ row }">
          <UiBadge :tone="row.is_active ? 'success' : 'danger'">
            {{ row.is_active ? t('admin.statusNormal') : t('admin.tenantStatusDisabled') }}
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
              {{ t('admin.tenantActionSwitch') }}
            </UiButton>
            <UiButton variant="text" size="sm" @click="openMembersDialog(row)">{{ t('admin.tenantActionMembers') }}</UiButton>
            <UiDropdown>
              <template #trigger>
                <UiButton variant="text" size="sm">
                  {{ t('common.more') }}<ChevronDown class="size-4" />
                </UiButton>
              </template>
              <template #default="{ close }">
                <UiDropdownItem @select="close(); openEditDialog(row)">{{ t('common.edit') }}</UiDropdownItem>
                <UiDropdownItem
                  danger
                  :disabled="!!row.is_system"
                  @select="close(); handleDelete(row)"
                >
                  {{ t('common.delete') }}
                </UiDropdownItem>
              </template>
            </UiDropdown>
          </div>
        </template>
      </UiTable>
    </section>

    <UiDialog v-model="dialogVisible" :title="editMode ? t('admin.tenantDialogEdit') : t('admin.tenantDialogAdd')" width="480px">
      <div class="flex flex-col gap-4">
        <UiFormItem :label="t('admin.tenantFieldSlug')" required :error="errors.slug" :hint="editMode ? t('admin.tenantHintSlug') : ''">
          <UiInput
            v-model="form.slug"
            :disabled="editMode"
            :placeholder="t('admin.tenantPhSlug')"
          />
        </UiFormItem>
        <UiFormItem :label="t('admin.tenantFieldName')" required :error="errors.name">
          <UiInput v-model="form.name" :placeholder="t('admin.tenantPhName')" />
        </UiFormItem>
        <UiFormItem v-if="editMode" :label="t('common.status')">
          <div class="flex items-center gap-2">
            <UiSwitch v-model="form.is_active" />
            <span class="text-sm text-fg-secondary">{{ form.is_active ? t('common.enabled') : t('common.disabled') }}</span>
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

    <UiDialog
      v-model="membersDialogVisible"
      :title="t('admin.tenantMembersTitle', { name: memberTenant?.name || '' })"
      width="900px"
    >
      <div class="member-add">
        <UiInput v-model="memberForm.identifier" :placeholder="t('admin.tenantPhMemberIdentifier')" />
        <UiSelect v-model="memberForm.role" :options="roleSelectOptions" :placeholder="t('admin.tenantPhMemberRole')" />
        <UiButton :loading="addingMember" @click="handleAddMember">{{ t('common.add') }}</UiButton>
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
          <UiBadge v-if="row.is_superuser" tone="danger">{{ t('common.yes') }}</UiBadge>
          <span v-else class="t-caption">—</span>
        </template>
        <template #cell-mstatus="{ row }">
          <UiBadge :tone="row.membership_active ? 'success' : 'danger'">
            {{ row.membership_active ? t('admin.statusNormal') : t('admin.statusDisabled') }}
          </UiBadge>
        </template>
        <template #cell-actions="{ row }">
          <div class="flex justify-end">
            <UiButton variant="danger-text" size="sm" @click="handleRemoveMember(row)">{{ t('admin.tenantMemberRemove') }}</UiButton>
          </div>
        </template>
      </UiTable>
    </UiDialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
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
const { t } = useI18n()

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

const tenantColumns = computed<TableColumn[]>(() => [
  { key: 'id', label: 'ID', width: 60 },
  { key: 'slug', label: t('admin.tenantColSlug'), minWidth: 180 },
  { key: 'name', label: t('admin.tenantColName'), minWidth: 160 },
  { key: 'status', label: t('common.status'), width: 100 },
  { key: 'user_count', label: t('admin.tenantColUserCount'), width: 80, align: 'center' },
  { key: 'task_count', label: t('admin.tenantColTaskCount'), width: 80, align: 'center' },
  { key: 'created_at', label: t('common.createdAt'), width: 160 },
  { key: 'actions', label: t('common.actions'), width: 150, align: 'right', fixed: 'right' },
])

const memberColumns = computed<TableColumn[]>(() => [
  { key: 'username', label: t('admin.colUsername'), minWidth: 130 },
  { key: 'email', label: t('admin.colEmail'), minWidth: 200 },
  { key: 'role', label: t('admin.colRole'), width: 140 },
  { key: 'superuser', label: t('admin.tenantColSuperuser'), width: 120 },
  { key: 'mstatus', label: t('common.status'), width: 100 },
  { key: 'actions', label: t('common.actions'), width: 100, align: 'right', fixed: 'right' },
])

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
    if (!slug) errors.slug = t('admin.tenantValSlugRequired')
    else if (!/^[a-z0-9-]+$/.test(slug)) errors.slug = t('admin.tenantValSlugFormat')
    else if (slug.length < 2 || slug.length > 50) errors.slug = t('admin.tenantValSlugLength')
  }
  const name = form.name.trim()
  if (!name) errors.name = t('admin.tenantValNameRequired')
  else if (name.length > 100) errors.name = t('admin.tenantValNameLength')
  return !errors.slug && !errors.name
}

async function fetchTenants() {
  loading.value = true
  try {
    const { data } = await listTenants()
    tenants.value = data.data || []
  } catch (err: unknown) {
    const e = err as { response?: { data?: { message?: string } } }
    toast.error(e.response?.data?.message || t('admin.tenantLoadFailed'))
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
    toast.error(e.response?.data?.message || t('admin.tenantLoadRolesFailed'))
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
      await updateTenant(editTenantId.value as number, { name: form.name, is_active: form.is_active })
      toast.success(t('common.saveSuccess'))
    } else {
      await createTenant({ slug: form.slug, name: form.name })
      toast.success(t('admin.toastCreated'))
    }
    dialogVisible.value = false
    fetchTenants()
  } catch (err: unknown) {
    const e = err as { response?: { data?: { message?: string } } }
    toast.error(e.response?.data?.message || t('common.operationFailed'))
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row: Record<string, unknown>) {
  const r = row as TenantRow
  if (r.is_system) {
    toast.warning(t('admin.tenantSystemCannotDelete'))
    return
  }
  const ok = await confirm({
    title: t('admin.confirmDeleteTitle'),
    message: t('admin.tenantDeleteMsg', { name: r.name, slug: r.slug }),
    tone: 'danger',
    confirmText: t('common.delete'),
  })
  if (!ok) return
  try {
    await deleteTenant(r.id)
    toast.success(t('common.deleteSuccess'))
    fetchTenants()
  } catch (err: unknown) {
    const e = err as { response?: { data?: { message?: string } } }
    toast.error(e.response?.data?.message || t('admin.deleteFailed'))
  }
}

async function handleSwitchTo(row: Record<string, unknown>) {
  const r = row as TenantRow
  const ok = await confirm({
    title: t('admin.tenantSwitchTitle'),
    message: t('admin.tenantSwitchMsg', { name: r.name }),
    confirmText: t('admin.tenantActionSwitch'),
  })
  if (!ok) return
  try {
    await authStore.switchTenant(r.id)
    toast.success(t('admin.tenantSwitchedTo', { name: r.name }))
    setTimeout(() => window.location.reload(), 300)
  } catch (err: unknown) {
    const e = err as { response?: { data?: { message?: string } } }
    toast.error(e.response?.data?.message || t('admin.tenantSwitchFailed'))
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
    toast.error(e.response?.data?.message || t('admin.tenantLoadMembersFailed'))
  } finally {
    membersLoading.value = false
  }
}

async function handleAddMember() {
  if (!memberTenant.value) return
  if (!memberForm.identifier.trim()) {
    toast.warning(t('admin.tenantValMemberIdentifierRequired'))
    return
  }
  addingMember.value = true
  try {
    await addTenantMember(memberTenant.value.id, {
      identifier: memberForm.identifier.trim(),
      role: memberForm.role,
    })
    toast.success(t('admin.tenantMemberAdded'))
    resetMemberForm()
    await Promise.all([fetchMembers(), fetchTenants()])
  } catch (err: unknown) {
    const e = err as { response?: { data?: { message?: string } } }
    toast.error(e.response?.data?.message || t('admin.tenantAddMemberFailed'))
  } finally {
    addingMember.value = false
  }
}

async function handleRemoveMember(row: Record<string, unknown>) {
  const r = row as MemberRow
  if (!memberTenant.value) return
  const ok = await confirm({
    title: t('admin.tenantRemoveMemberTitle'),
    message: t('admin.tenantRemoveMemberMsg', { tenant: memberTenant.value.name, name: r.username }),
    tone: 'danger',
    confirmText: t('admin.tenantMemberRemove'),
  })
  if (!ok) return
  try {
    await removeTenantMember(memberTenant.value.id, r.id)
    toast.success(t('admin.tenantMemberRemoved'))
    await Promise.all([fetchMembers(), fetchTenants()])
  } catch (err: unknown) {
    const e = err as { response?: { data?: { message?: string } } }
    toast.error(e.response?.data?.message || t('admin.tenantRemoveMemberFailed'))
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
