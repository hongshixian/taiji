<template>
  <LoaderCircle
    class="animate-spin text-brand"
    :style="{ width: size + 'px', height: size + 'px' }"
  />
</template>

<script setup lang="ts">
import { LoaderCircle } from 'lucide-vue-next'

withDefaults(
  defineProps<{
    size?: number
  }>(),
  { size: 16 },
)
</script>
