<template>
  <UiSelect
    v-if="activeMemberships.length > 0"
    :model-value="currentId"
    :options="options"
    :disabled="activeMemberships.length <= 1"
    class="w-[200px]"
    @update:model-value="handleSwitch"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { toast } from '@/lib/toast'
import { useAuthStore } from '@/stores/auth'
import UiSelect, { type SelectOption } from '@/components/ui/Select.vue'

const authStore = useAuthStore()

interface Membership {
  id: number
  tenant_id: number
  tenant_name: string
  tenant_slug: string
  role_name?: string
  role?: string
  is_active?: boolean
}

const activeMemberships = computed<Membership[]>(() =>
  ((authStore.user?.memberships as Membership[] | undefined) || []).filter((m) => m.is_active),
)
const currentId = computed(() => authStore.currentTenant?.id ?? null)

const options = computed<SelectOption[]>(() =>
  activeMemberships.value.map((m) => ({
    label: m.tenant_name,
    value: m.tenant_id,
    badge: m.tenant_slug,
  })),
)

async function handleSwitch(tenantId: string | number | null) {
  if (tenantId == null || tenantId === currentId.value) return
  try {
    await authStore.switchTenant(tenantId as number)
    toast.success(`已切换到租户「${authStore.currentTenant?.name}」`)
    setTimeout(() => window.location.reload(), 300)
  } catch (err: unknown) {
    const e = err as { response?: { data?: { message?: string } } }
    toast.error(e.response?.data?.message || '切换失败')
  }
}
</script>
