<template>
  <div v-bind="rest" :class="cn('rounded-lg border border-line bg-surface shadow-xs', $attrs.class as string)">
    <slot />
  </div>
</template>

<script setup lang="ts">
import { computed, useAttrs } from 'vue'
import { cn } from '@/lib/utils'
defineOptions({ inheritAttrs: false })
const attrs = useAttrs()
const rest = computed(() => {
  const { class: _c, ...others } = attrs
  return others
})
</script>
