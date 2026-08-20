<template>
  <UiSelect
    v-if="tenants.length > 0"
    :model-value="currentTenantId"
    :options="options"
    :disabled="tenants.length <= 1 || switching"
    class="w-[220px]"
    @update:model-value="handleSwitch"
  />
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { toast } from '@/lib/toast'
import { useAuthStore } from '@/stores/auth'
import UiSelect, { type SelectOption } from '@/components/ui/Select.vue'

const authStore = useAuthStore()
const switching = ref(false)
const tenants = computed(() => authStore.tenants.filter((tenant) => tenant.enabled))
const currentTenantId = computed(() => authStore.currentTenant?.id ?? null)

const options = computed<SelectOption[]>(() =>
  tenants.value.map((tenant) => ({
    label: tenant.name,
    value: tenant.id,
    badge: tenant.tenant_type === 'personal' ? '个人' : tenant.role === 'tenant_admin' ? '管理员' : '成员',
  })),
)

async function handleSwitch(tenantId: string | number | null) {
  if (tenantId == null || Number(tenantId) === currentTenantId.value) return
  switching.value = true
  try {
    await authStore.switchTenant(Number(tenantId))
    toast.success(`已切换到租户「${authStore.currentTenant?.name}」`)
    window.location.reload()
  } catch (err: unknown) {
    const e = err as { response?: { data?: { message?: string } } }
    toast.error(e.response?.data?.message || '切换失败')
  } finally {
    switching.value = false
  }
}
</script>
