<template>
  <el-select
    :model-value="currentId"
    :disabled="activeMemberships.length <= 1"
    class="tenant-select"
    size="small"
    fit-input-width
    @change="handleSwitch"
  >
    <template #prefix>
      <el-icon class="tenant-icon"><OfficeBuilding /></el-icon>
    </template>
    <el-option
      v-for="m in activeMemberships"
      :key="m.id"
      :label="m.tenant_name"
      :value="m.tenant_id"
    >
      <div class="tenant-option">
        <span class="ti-name">{{ m.tenant_name }}</span>
        <span class="ti-slug">{{ m.tenant_slug }}</span>
        <el-tag size="small" effect="plain">{{ m.role_name || m.role }}</el-tag>
      </div>
    </el-option>
  </el-select>
</template>

<script setup>
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()

const activeMemberships = computed(() => {
  return (authStore.user?.memberships || []).filter((m) => m.is_active)
})
const currentId = computed(() => authStore.currentTenant?.id)

async function handleSwitch(tenantId) {
  if (tenantId === currentId.value) return
  try {
    await authStore.switchTenant(tenantId)
    ElMessage.success(`已切换到租户「${authStore.currentTenant?.name}」`)
    setTimeout(() => window.location.reload(), 300)
  } catch (err) {
    ElMessage.error(err.response?.data?.message || '切换失败')
  }
}
</script>

<style scoped>
.tenant-select {
  width: 200px;
}
.tenant-select :deep(.el-select__wrapper) {
  min-height: 36px;
  border-radius: var(--radius-md);
  background: var(--bg-surface-sunken);
  box-shadow: 0 0 0 1px var(--border-subtle) inset;
}
.tenant-select :deep(.el-select__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--border-default) inset;
}
.tenant-icon {
  font-size: 15px;
  color: var(--violet-600);
}
[data-theme="dark"] .tenant-icon,
html.dark .tenant-icon { color: var(--violet-300); }
.tenant-option {
  display: flex;
  align-items: center;
  gap: var(--space-5);
  min-width: 240px;
}
.ti-name {
  font-weight: var(--weight-medium);
  flex: 1;
}
.ti-slug {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--fg-tertiary);
}
@media (max-width: 768px) {
  .tenant-select { width: 140px; }
}
</style>
