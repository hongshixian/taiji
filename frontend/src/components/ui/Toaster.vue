<template>
  <Teleport to="body">
    <div class="pointer-events-none fixed left-1/2 top-4 z-[200] flex -translate-x-1/2 flex-col gap-2">
      <TransitionGroup
        enter-active-class="transition duration-200 ease-out"
        enter-from-class="opacity-0 -translate-y-2"
        leave-active-class="transition duration-150 ease-in"
        leave-to-class="opacity-0 -translate-y-1"
      >
        <div
          v-for="t in toasts"
          :key="t.id"
          :class="cn(
            'pointer-events-auto flex items-center gap-2 rounded-lg border px-4 py-2.5 text-sm shadow-lg',
            toneClass(t.tone),
          )"
        >
          <component :is="icon(t.tone)" class="size-4 shrink-0" />
          <span>{{ t.message }}</span>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { CircleCheck, CircleAlert, TriangleAlert, Info } from 'lucide-vue-next'
import { toasts, type ToastTone } from '@/lib/toast'
import { cn } from '@/lib/utils'

function toneClass(tone: ToastTone) {
  return {
    success: 'border-success/30 bg-success-soft text-success',
    error: 'border-danger/30 bg-danger-soft text-danger',
    warning: 'border-warning/30 bg-warning-soft text-warning',
    info: 'border-info/30 bg-info-soft text-info',
  }[tone]
}
function icon(tone: ToastTone) {
  return { success: CircleCheck, error: CircleAlert, warning: TriangleAlert, info: Info }[tone]
}
</script>
