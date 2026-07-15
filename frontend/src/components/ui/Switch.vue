<template>
  <button
    type="button"
    role="switch"
    :aria-checked="modelValue"
    :disabled="disabled"
    :class="cn(
      'inline-flex h-5 w-9 shrink-0 items-center rounded-full p-0.5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/40',
      modelValue ? 'bg-brand' : 'bg-surface-muted',
      disabled && 'opacity-50 pointer-events-none',
    )"
    @click="toggle"
  >
    <span
      :class="cn(
        'size-4 rounded-full bg-white shadow-xs transition-transform',
        modelValue && 'translate-x-4',
      )"
    />
  </button>
</template>

<script setup lang="ts">
import { cn } from '@/lib/utils'

const props = withDefaults(
  defineProps<{
    modelValue?: boolean
    disabled?: boolean
  }>(),
  { modelValue: false, disabled: false },
)

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

function toggle() {
  if (props.disabled) return
  emit('update:modelValue', !props.modelValue)
}
</script>
