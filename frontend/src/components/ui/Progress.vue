<template>
  <div class="flex items-center gap-2 w-full">
    <div
      class="w-full rounded-full bg-surface-muted overflow-hidden"
      :style="{ height: strokeWidth + 'px' }"
    >
      <div
        v-if="indeterminate"
        :class="cn('h-full rounded-full progress-indeterminate', fillColor)"
      />
      <div
        v-else
        :class="cn('h-full rounded-full transition-all', fillColor)"
        :style="{ width: clamped + '%' }"
      />
    </div>
    <span v-if="showText && !indeterminate" class="text-sm text-fg-secondary tabular-nums shrink-0">
      {{ clamped }}%
    </span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { cn } from '@/lib/utils'

const props = withDefaults(
  defineProps<{
    percentage?: number
    indeterminate?: boolean
    strokeWidth?: number
    showText?: boolean
    status?: 'success' | 'warning' | 'danger'
  }>(),
  { percentage: 0, indeterminate: false, strokeWidth: 8, showText: true },
)

const clamped = computed(() => Math.min(100, Math.max(0, Math.round(props.percentage))))

const fillColor = computed(() => {
  switch (props.status) {
    case 'success':
      return 'bg-success'
    case 'warning':
      return 'bg-warning'
    case 'danger':
      return 'bg-danger'
    default:
      return 'bg-brand'
  }
})
</script>

<style scoped>
.progress-indeterminate {
  width: 30%;
  animation: progress-slide 1.2s ease-in-out infinite;
}

@keyframes progress-slide {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(333%);
  }
}
</style>
