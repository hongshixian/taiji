<template>
  <div class="rounded-md border border-line">
    <button
      type="button"
      class="flex w-full items-center justify-between px-4 py-3 text-sm font-medium text-fg transition-colors hover:bg-surface-sunken"
      @click="open = !open"
    >
      <span>{{ title }}</span>
      <ChevronDown :class="cn('size-4 text-fg-tertiary transition-transform', open && 'rotate-180')" />
    </button>
    <div v-show="open" class="border-t border-line px-4 py-3">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ChevronDown } from 'lucide-vue-next'
import { cn } from '@/lib/utils'

withDefaults(defineProps<{ title?: string; defaultOpen?: boolean }>(), { defaultOpen: false })
const open = ref(false)
</script>
