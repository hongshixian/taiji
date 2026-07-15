<template>
  <div class="flex flex-col gap-1.5" :class="inline && 'sm:flex-row sm:items-center sm:gap-4'">
    <label
      v-if="label"
      :class="cn('text-sm font-medium text-fg', inline && 'sm:w-32 sm:shrink-0 sm:text-right')"
    >
      {{ label }}
      <span v-if="required" class="text-danger">*</span>
    </label>
    <div class="flex-1">
      <slot />
      <p v-if="error" class="mt-1 text-xs text-danger">{{ error }}</p>
      <p v-else-if="hint" class="mt-1 text-xs text-fg-tertiary">{{ hint }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { cn } from '@/lib/utils'
defineProps<{
  label?: string
  required?: boolean
  error?: string
  hint?: string
  inline?: boolean
}>()
</script>
