<template>
  <div class="page-shell page-shell--wide role-management">
    <header class="page-header">
      <span class="page-header__eyebrow t-eyebrow">{{ t('admin.roleEyebrow') }}</span>
      <div class="page-header__row">
        <h1 class="page-header__title">{{ t('admin.roleTitle') }}</h1>
        <UiButton v-if="has('role:write')" @click="openCreateDialog">
          <template #icon><Plus class="size-4" /></template>
          {{ t('admin.roleAdd') }}
        </UiButton>
      </div>
      <p class="page-header__lede">
        {{ t('admin.roleLede') }}
      </p>
    </header>

    <section class="data-section" data-density="compact">
      <UiTable :columns="columns" :data="roles" row-key="id" stripe :loading="loading">
        <template #cell-name="{ row }">
          <span class="role-name">{{ row.name }}</span>
          <UiBadge v-if="row.is_system" tone="neutral" class="ml-2">{{ t('admin.badgeSystem') }}</UiBadge>
          <UiBadge v-else tone="info" class="ml-2">{{ t('admin.roleBadgeCurrentTenant') }}</UiBadge>
        </template>
        <template #cell-perms="{ row }">
          <span class="t-mono">{{ t('admin.rolePermCount', { n: (row.permissions as string[]).length }) }}</span>
        </template>
        <template #cell-actions="{ row }">
          <div class="flex justify-end gap-1">
            <UiButton
              v-if="has('role:write') && !row.is_system"
              variant="text"
              size="sm"
              @click="openEditDialog(row)"
            >
              {{ t('common.edit') }}
            </UiButton>
            <UiButton
              v-if="has('role:delete') && !row.is_system"
              variant="danger-text"
              size="sm"
              @click="handleDelete(row)"
            >
              {{ t('common.delete') }}
            </UiButton>
          </div>
        </template>
      </UiTable>
    </section>

    <UiDialog v-model="dialogVisible" :title="editMode ? t('admin.roleDialogEdit') : t('admin.roleDialogAdd')" width="600px">
      <div class="flex flex-col gap-4">
        <UiFormItem :label="t('admin.roleFieldName')" required>
          <UiInput
            v-model="form.name"
            :disabled="editMode && form.is_system"
            :placeholder="t('admin.rolePhName')"
          />
        </UiFormItem>
        <UiFormItem :label="t('common.description')">
          <UiTextarea v-model="form.description" :rows="2" />
        </UiFormItem>
        <UiFormItem :label="t('admin.roleFieldPermissions')">
          <div class="flex flex-col gap-6">
            <div
              v-for="(group, prefix) in groupedPermissions"
              :key="prefix"
              class="perm-group"
            >
              <span class="t-eyebrow perm-group-title">{{ groupLabel(prefix) }}</span>
              <label
                v-for="p in group"
                :key="p.code"
                class="flex cursor-pointer items-center gap-3 py-1"
              >
                <input
                  type="checkbox"
                  class="size-4 shrink-0 accent-brand"
                  :value="p.code"
                  :checked="form.permissions.includes(p.code)"
                  @change="togglePermission(p.code)"
                />
                <span class="perm-code">{{ p.code }}</span>
                <span class="perm-desc">{{ p.description }}</span>
              </label>
            </div>
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
import { listRoles, listAllPermissions, createRole, updateRole, deleteRole } from '@/api/admin'
import { usePermission } from '@/composables/usePermission'
import UiTable, { type TableColumn } from '@/components/ui/Table.vue'
import UiButton from '@/components/ui/Button.vue'
import UiBadge from '@/components/ui/Badge.vue'
import UiDialog from '@/components/ui/Dialog.vue'
import UiFormItem from '@/components/ui/FormItem.vue'
import UiInput from '@/components/ui/Input.vue'
import UiTextarea from '@/components/ui/Textarea.vue'

const { has } = usePermission()
const { t } = useI18n()

interface Permission {
  code: string
  description?: string
}
interface RoleRow {
  id: number
  name: string
  description?: string
  permissions: string[]
  is_system?: boolean
  [key: string]: unknown
}

const columns = computed<TableColumn[]>(() => [
  { key: 'id', label: 'ID', width: 60 },
  { key: 'name', label: t('admin.roleColName'), minWidth: 180 },
  { key: 'description', label: t('common.description'), minWidth: 220 },
  { key: 'perms', label: t('admin.roleColPermCount'), width: 120 },
  { key: 'actions', label: t('common.actions'), width: 160, align: 'right', fixed: 'right' },
])

const roles = ref<RoleRow[]>([])
const allPermissions = ref<Permission[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const editMode = ref(false)
const editRoleId = ref<number | null>(null)
const submitting = ref(false)

const form = reactive({
  name: '',
  description: '',
  permissions: [] as string[],
  is_system: false,
})

// 按前缀分组（user:/role:/task:/system:）
const groupedPermissions = computed<Record<string, Permission[]>>(() => {
  const groups: Record<string, Permission[]> = {}
  allPermissions.value.forEach((p) => {
    const prefix = p.code.split(':')[0]
    if (!groups[prefix]) groups[prefix] = []
    groups[prefix].push(p)
  })
  return groups
})

function groupLabel(prefix: string) {
  const map: Record<string, string> = { user: t('admin.roleGroupUser'), role: t('admin.roleGroupRole'), task: t('admin.roleGroupTask'), system: t('admin.roleGroupSystem') }
  return map[prefix] || prefix
}

function togglePermission(code: string) {
  const idx = form.permissions.indexOf(code)
  if (idx === -1) form.permissions.push(code)
  else form.permissions.splice(idx, 1)
}

async function fetchData() {
  loading.value = true
  try {
    const [rolesResp, permsResp] = await Promise.all([listRoles(), listAllPermissions()])
    roles.value = rolesResp.data.data
    allPermissions.value = permsResp.data.data
  } catch (err: unknown) {
    const e = err as { response?: { data?: { message?: string } } }
    toast.error(e.response?.data?.message || t('common.loadFailed'))
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

function openEditDialog(row: Record<string, unknown>) {
  const r = row as RoleRow
  editMode.value = true
  editRoleId.value = r.id
  form.name = r.name
  form.description = r.description || ''
  form.permissions = [...r.permissions]
  form.is_system = !!r.is_system
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!form.name.trim()) {
    toast.warning(t('admin.roleValNameRequired'))
    return
  }
  submitting.value = true
  try {
    if (editMode.value) {
      const payload: Record<string, unknown> = {
        description: form.description,
        permissions: form.permissions,
      }
      if (!form.is_system) payload.name = form.name
      await updateRole(editRoleId.value as number, payload)
      toast.success(t('common.saveSuccess'))
    } else {
      await createRole({
        name: form.name,
        description: form.description,
        permissions: form.permissions,
      })
      toast.success(t('admin.toastCreated'))
    }
    dialogVisible.value = false
    fetchData()
  } catch (err: unknown) {
    const e = err as { response?: { data?: { message?: string } } }
    toast.error(e.response?.data?.message || t('common.operationFailed'))
  } finally {
    submitting.value = false
  }
}

async function handleDelete(row: Record<string, unknown>) {
  const r = row as RoleRow
  const ok = await confirm({
    title: t('admin.confirmDeleteTitle'),
    message: t('admin.roleDeleteMsg', { name: r.name }),
    tone: 'danger',
    confirmText: t('common.delete'),
  })
  if (!ok) return
  try {
    await deleteRole(r.id)
    toast.success(t('common.deleteSuccess'))
    fetchData()
  } catch (err: unknown) {
    const e = err as { response?: { data?: { message?: string } } }
    toast.error(e.response?.data?.message || t('admin.deleteFailed'))
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
.data-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.role-name {
  font-weight: var(--weight-semibold);
  color: var(--fg-primary);
}

/* 权限分组 */
.perm-group {
  width: 100%;
  padding-bottom: var(--space-5);
  border-bottom: 1px solid var(--border-subtle);
}
.perm-group:last-child {
  border-bottom: none;
  padding-bottom: 0;
}
.perm-group-title {
  display: block;
  margin-bottom: var(--space-5);
  color: var(--violet-600);
  letter-spacing: 0.18em;
}
[data-theme='dark'] .perm-group-title,
html.dark .perm-group-title {
  color: var(--violet-300);
}
.perm-code {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--fg-primary);
  min-width: 140px;
}
.perm-desc {
  color: var(--fg-secondary);
  font-size: var(--text-sm);
}

@media (max-width: 768px) {
  .page-header__row {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
