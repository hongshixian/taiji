<template>
  <UiFormItem :label="field.label || field.key" :hint="field.help">
    <!-- int / float -->
    <UiInputNumber
      v-if="field.type === 'int' || field.type === 'float'"
      :model-value="(value as number | null)"
      :min="field.min"
      :max="field.max"
      :step="field.type === 'float' ? (field.step || 0.1) : 1"
      :precision="field.type === 'float' ? (field.precision ?? 2) : 0"
      block
      @update:model-value="onUpdate"
    />

    <!-- bool -->
    <UiSwitch
      v-else-if="field.type === 'bool'"
      :model-value="!!value"
      @update:model-value="onUpdate"
    />

    <!-- enum / select -->
    <UiSelect
      v-else-if="field.type === 'enum' || field.type === 'select'"
      :model-value="(value as string | number | null)"
      :options="selectOptions"
      filterable
      @update:model-value="onUpdate"
    />

    <!-- string (default) -->
    <UiInput
      v-else
      :model-value="(value as string) ?? ''"
      :placeholder="field.placeholder || ''"
      @update:model-value="onUpdate"
    />
  </UiFormItem>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import type { SuiteConfigField } from '@/api/types'
import UiFormItem from './ui/FormItem.vue'
import UiInput from './ui/Input.vue'
import UiInputNumber from './ui/InputNumber.vue'
import UiSwitch from './ui/Switch.vue'
import UiSelect, { type SelectOption } from './ui/Select.vue'

const props = defineProps<{
  field: SuiteConfigField
  modelValue?: unknown
}>()
const emit = defineEmits<{ 'update:modelValue': [value: unknown] }>()

const value = computed(() =>
  props.modelValue !== undefined ? props.modelValue : (props.field.default ?? null),
)

const selectOptions = computed<SelectOption[]>(() =>
  (props.field.options || []).map((o) =>
    typeof o === 'object'
      ? { label: String((o as { label: string }).label), value: (o as { value: unknown }).value as string | number }
      : { label: String(o), value: o as string | number },
  ),
)

onMounted(() => {
  if (props.modelValue === undefined && props.field.default !== undefined) {
    emit('update:modelValue', props.field.default)
  }
})

function onUpdate(v: unknown) {
  emit('update:modelValue', v)
}
</script>
