<template>
  <textarea
    :value="modelValue"
    :placeholder="placeholder"
    :rows="rows"
    :maxlength="maxlength"
    :disabled="disabled"
    class="w-full rounded-md border border-line-strong bg-surface px-3 py-2 text-sm text-fg placeholder:text-fg-tertiary focus:outline-none focus:border-brand focus:ring-2 focus:ring-brand/30 transition-colors disabled:opacity-60 disabled:pointer-events-none"
    @input="onInput"
  />
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    modelValue?: string
    placeholder?: string
    rows?: number
    maxlength?: number
    disabled?: boolean
  }>(),
  { modelValue: '', rows: 3 },
)

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

function onInput(e: Event) {
  emit('update:modelValue', (e.target as HTMLTextAreaElement).value)
}
</script>
