<template>
  <div
    :class="cn(
      'flex items-center gap-2 rounded-md border bg-surface px-3 transition-colors h-9',
      focused ? 'border-brand ring-2 ring-brand/30' : 'border-line-strong',
      disabled && 'opacity-60 pointer-events-none',
    )"
  >
    <span v-if="$slots.prefix" class="text-fg-tertiary flex items-center">
      <slot name="prefix" />
    </span>
    <input
      :type="revealed ? 'text' : type"
      :value="modelValue"
      :placeholder="placeholder"
      :disabled="disabled"
      :autocomplete="autocomplete"
      :maxlength="maxlength"
      class="w-full bg-transparent text-sm text-fg placeholder:text-fg-tertiary focus:outline-none"
      @input="onInput"
      @focus="focused = true"
      @blur="focused = false"
      @keydown.enter="$emit('enter')"
    />
    <button
      v-if="type === 'password'"
      type="button"
      class="text-fg-tertiary hover:text-fg flex items-center"
      tabindex="-1"
      @click="revealed = !revealed"
    >
      <EyeOff v-if="revealed" class="size-4" />
      <Eye v-else class="size-4" />
    </button>
    <span v-if="$slots.suffix" class="text-fg-tertiary flex items-center">
      <slot name="suffix" />
    </span>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Eye, EyeOff } from 'lucide-vue-next'
import { cn } from '@/lib/utils'

withDefaults(
  defineProps<{
    modelValue?: string | number
    type?: string
    placeholder?: string
    disabled?: boolean
    autocomplete?: string
    maxlength?: number
  }>(),
  { type: 'text', modelValue: '' },
)

const emit = defineEmits<{
  'update:modelValue': [value: string]
  enter: []
}>()

const focused = ref(false)
const revealed = ref(false)

function onInput(e: Event) {
  emit('update:modelValue', (e.target as HTMLInputElement).value)
}
</script>
