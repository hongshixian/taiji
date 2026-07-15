<template>
  <div class="flex flex-col items-center justify-center py-12">
    <Inbox class="size-10 text-fg-tertiary" />
    <p class="text-sm text-fg-tertiary mt-3">{{ description }}</p>
    <div v-if="$slots.default" class="mt-4">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { Inbox } from 'lucide-vue-next'

withDefaults(
  defineProps<{
    description?: string
  }>(),
  { description: '暂无数据' },
)
</script>
