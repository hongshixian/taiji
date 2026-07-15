<template>
  <label :for="props.for" class="text-sm font-medium text-fg">
    <slot />
  </label>
</template>

<script setup lang="ts">
const props = defineProps<{
  for?: string
}>()
</script>
