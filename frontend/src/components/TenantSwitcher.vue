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
  width: 180px;
}
.tenant-select :deep(.el-select__wrapper) {
  min-height: 32px;
  border-radius: var(--taiji-radius-sm);
  background: var(--el-fill-color-light);
}
.tenant-icon {
  font-size: 15px;
  color: var(--taiji-accent);
}
.tenant-option {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 240px;
}
.ti-name {
  font-weight: 500;
  flex: 1;
}
.ti-slug {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
@media (max-width: 768px) {
  .tenant-select { width: 132px; }
}
</style>
