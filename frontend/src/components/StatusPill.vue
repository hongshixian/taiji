<template>
  <span class="status-pill" :data-tone="tone">
    <span v-if="dot" class="status-pill__dot" />
    <slot>{{ label }}</slot>
  </span>
</template>

<script setup>
defineProps({
  tone: { type: String, default: 'neutral' },  // success | danger | warning | info | neutral
  label: { type: String, default: '' },
  dot: { type: Boolean, default: false },
})
</script>
