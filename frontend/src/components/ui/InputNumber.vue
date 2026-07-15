<template>
  <div
    :class="cn(
      'inline-flex h-9 items-center rounded-md border bg-surface',
      focused ? 'border-brand ring-2 ring-brand/30' : 'border-line-strong',
      disabled && 'opacity-60 pointer-events-none',
      block ? 'w-full' : 'w-36',
    )"
  >
    <button
      type="button"
      class="flex h-full w-8 shrink-0 items-center justify-center text-fg-tertiary hover:text-fg"
      tabindex="-1"
      @click="step(-1)"
    >
      <Minus class="size-3.5" />
    </button>
    <input
      :value="modelValue ?? ''"
      type="text"
      inputmode="decimal"
      :placeholder="placeholder"
      :disabled="disabled"
      class="w-full min-w-0 border-x border-line bg-transparent px-2 text-center text-sm text-fg placeholder:text-fg-tertiary focus:outline-none"
      @input="onInput"
      @focus="focused = true"
      @blur="focused = false"
    />
    <button
      type="button"
      class="flex h-full w-8 shrink-0 items-center justify-center text-fg-tertiary hover:text-fg"
      tabindex="-1"
      @click="step(1)"
    >
      <Plus class="size-3.5" />
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Plus, Minus } from 'lucide-vue-next'
import { cn } from '@/lib/utils'

const props = withDefaults(
  defineProps<{
    modelValue?: number | null
    min?: number
    max?: number
    step?: number
    placeholder?: string
    disabled?: boolean
    block?: boolean
    precision?: number
  }>(),
  { step: 1, block: false },
)
const emit = defineEmits<{ 'update:modelValue': [value: number | null] }>()
const focused = ref(false)

function clamp(v: number): number {
  if (props.min != null && v < props.min) v = props.min
  if (props.max != null && v > props.max) v = props.max
  if (props.precision != null) v = Number(v.toFixed(props.precision))
  return v
}
function onInput(e: Event) {
  const raw = (e.target as HTMLInputElement).value.trim()
  if (raw === '') return emit('update:modelValue', null)
  const n = Number(raw)
  if (!Number.isNaN(n)) emit('update:modelValue', clamp(n))
}
function step(dir: number) {
  const cur = props.modelValue ?? 0
  emit('update:modelValue', clamp(cur + dir * (props.step ?? 1)))
}
</script>
