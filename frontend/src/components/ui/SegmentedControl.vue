<template>
  <div class="inline-flex items-center gap-1 rounded-md border border-line bg-surface-sunken p-0.5">
    <button
      v-for="opt in options"
      :key="String(opt.value)"
      type="button"
      :class="cn(
        'rounded-sm px-3 py-1 text-sm font-medium transition-colors',
        modelValue === opt.value
          ? 'bg-surface text-fg shadow-xs'
          : 'text-fg-secondary hover:text-fg',
      )"
      @click="$emit('update:modelValue', opt.value)"
    >
      {{ opt.label }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { cn } from '@/lib/utils'

export interface SegOption {
  label: string
  value: string | number | null
}

defineProps<{
  modelValue: string | number | null
  options: SegOption[]
}>()
defineEmits<{ 'update:modelValue': [value: string | number | null] }>()
</script>
