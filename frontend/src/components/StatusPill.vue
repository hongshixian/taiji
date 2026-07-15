<template>
  <UiBadge :tone="tone" :dot="dot">
    <slot>{{ label }}</slot>
  </UiBadge>
</template>

<script setup lang="ts">
import UiBadge from './ui/Badge.vue'
defineProps<{
  tone?: 'success' | 'danger' | 'warning' | 'info' | 'neutral' | 'brand'
  label?: string
  dot?: boolean
}>()
</script>
