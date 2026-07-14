<template>
  <el-form-item :label="field.label || field.key">
    <!-- int / float -->
    <el-input-number
      v-if="field.type === 'int' || field.type === 'float'"
      :model-value="value"
      :min="field.min"
      :max="field.max"
      :step="field.type === 'float' ? (field.step || 0.1) : 1"
      :precision="field.type === 'float' ? (field.precision ?? 2) : 0"
      controls-position="right"
      @update:model-value="onUpdate"
    />

    <!-- bool -->
    <el-switch
      v-else-if="field.type === 'bool'"
      :model-value="!!value"
      @update:model-value="onUpdate"
    />

    <!-- select -->
    <el-select
      v-else-if="field.type === 'enum' || field.type === 'select'"
      :model-value="value"
      style="width:100%"
      @update:model-value="onUpdate"
    >
      <el-option
        v-for="o in (field.options || [])"
        :key="typeof o === 'object' ? o.value : o"
        :label="typeof o === 'object' ? o.label : o"
        :value="typeof o === 'object' ? o.value : o"
      />
    </el-select>

    <!-- multi_select -->
    <el-select
      v-else-if="field.type === 'multi_select'"
      :model-value="value || []"
      multiple
      collapse-tags
      collapse-tags-tooltip
      style="width:100%"
      @update:model-value="onUpdate"
    >
      <el-option
        v-for="o in (field.options || [])"
        :key="typeof o === 'object' ? o.value : o"
        :label="typeof o === 'object' ? o.label : o"
        :value="typeof o === 'object' ? o.value : o"
      />
    </el-select>

    <!-- string (default) -->
    <el-input
      v-else
      :model-value="value ?? ''"
      :placeholder="field.placeholder || ''"
      @update:model-value="onUpdate"
    />

    <div v-if="field.help" class="dyn-help">{{ field.help }}</div>
  </el-form-item>
</template>

<script setup>
import { computed, onMounted } from 'vue'

const props = defineProps({
  field: { type: Object, required: true },
  modelValue: { default: undefined },
})
const emit = defineEmits(['update:modelValue'])

// 响应式：随 modelValue 或 field.default 变化
const value = computed(() =>
  props.modelValue !== undefined ? props.modelValue : (props.field.default ?? null),
)

// 挂载时若父级未提供值但字段有默认值，回写默认值到父 model
onMounted(() => {
  if (props.modelValue === undefined && props.field.default !== undefined) {
    emit('update:modelValue', props.field.default)
  }
})

function onUpdate(v) {
  emit('update:modelValue', v)
}
</script>

<style scoped>
.dyn-help {
  font-size: var(--text-xs);
  color: var(--fg-tertiary);
  margin-top: var(--space-2);
}
</style>
