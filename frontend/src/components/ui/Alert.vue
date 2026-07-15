<template>
  <div :class="cn('rounded-md border p-3 flex gap-2 items-start', styles.container)">
    <component :is="styles.icon" class="size-4 mt-0.5 shrink-0" />
    <div class="flex flex-col min-w-0 flex-1">
      <span v-if="title" class="font-medium text-sm">{{ title }}</span>
      <div class="text-sm">
        <slot />
      </div>
    </div>
    <button
      v-if="closable"
      type="button"
      class="shrink-0 opacity-70 hover:opacity-100 transition-opacity"
      @click="$emit('close')"
    >
      <X class="size-4" />
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Info, CheckCircle2, AlertTriangle, CircleAlert, X } from 'lucide-vue-next'
import { cn } from '@/lib/utils'

const props = withDefaults(
  defineProps<{
    type?: 'info' | 'success' | 'warning' | 'danger'
    title?: string
    closable?: boolean
  }>(),
  { type: 'info', closable: false },
)

defineEmits<{
  close: []
}>()

const styleMap = {
  info: { container: 'bg-info-soft text-info border-info/30', icon: Info },
  success: { container: 'bg-success-soft text-success border-success/30', icon: CheckCircle2 },
  warning: { container: 'bg-warning-soft text-warning border-warning/30', icon: AlertTriangle },
  danger: { container: 'bg-danger-soft text-danger border-danger/30', icon: CircleAlert },
} as const

const styles = computed(() => styleMap[props.type])
</script>
