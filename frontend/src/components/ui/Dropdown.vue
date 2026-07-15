<template>
  <PopoverRoot :open="open" @update:open="open = $event">
    <PopoverTrigger as-child>
      <slot name="trigger" />
    </PopoverTrigger>
    <PopoverPortal>
      <PopoverContent
        align="end"
        :side-offset="4"
        class="z-[60] min-w-[140px] overflow-hidden rounded-md border border-line bg-surface-raised p-1 shadow-lg"
      >
        <slot :close="() => (open = false)" />
      </PopoverContent>
    </PopoverPortal>
  </PopoverRoot>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { PopoverRoot, PopoverTrigger, PopoverPortal, PopoverContent } from 'reka-ui'
const open = ref(false)
</script>
