<template>
  <button
    type="button"
    :class="cn(
      'flex w-full cursor-pointer items-center gap-2 rounded-sm px-2.5 py-1.5 text-left text-sm transition-colors',
      danger ? 'text-danger hover:bg-danger-soft' : 'text-fg hover:bg-surface-sunken',
      disabled && 'pointer-events-none opacity-40',
    )"
    :disabled="disabled"
    @click="$emit('select')"
  >
    <slot />
  </button>
</template>

<script setup lang="ts">
import { cn } from '@/lib/utils'
defineProps<{ danger?: boolean; disabled?: boolean }>()
defineEmits<{ select: [] }>()
</script>
