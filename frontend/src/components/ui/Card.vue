<template>
  <div :class="cn('rounded-lg border border-line bg-surface shadow-xs', $attrs.class as string)">
    <slot />
  </div>
</template>

<script setup lang="ts">
import { cn } from '@/lib/utils'
defineOptions({ inheritAttrs: false })
</script>
