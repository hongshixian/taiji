<template>
  <span
    class="relative inline-flex"
    @mouseenter="open = true"
    @mouseleave="open = false"
    @focusin="open = true"
    @focusout="open = false"
  >
    <slot />
    <Transition
      enter-active-class="transition-opacity duration-150"
      leave-active-class="transition-opacity duration-100"
      enter-from-class="opacity-0"
      leave-to-class="opacity-0"
    >
      <span
        v-if="open && content"
        role="tooltip"
        class="absolute bottom-full left-1/2 z-50 mb-1 -translate-x-1/2 whitespace-nowrap rounded-md bg-fg px-2 py-1 text-xs text-canvas shadow-md"
      >
        {{ content }}
      </span>
    </Transition>
  </span>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  content?: string
}>()

const open = ref(false)
</script>
