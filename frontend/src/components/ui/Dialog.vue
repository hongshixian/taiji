<template>
  <DialogRoot :open="modelValue" @update:open="$emit('update:modelValue', $event)">
    <DialogPortal>
      <DialogOverlay class="fixed inset-0 z-50 bg-black/45 data-[state=open]:animate-in data-[state=open]:fade-in" />
      <DialogContent
        :class="cn(
          'fixed left-1/2 top-1/2 z-50 flex max-h-[85vh] w-[92vw] -translate-x-1/2 -translate-y-1/2 flex-col',
          'rounded-xl border border-line bg-surface-raised shadow-xl focus:outline-none',
        )"
        :style="{ maxWidth: width }"
        @interact-outside="onInteractOutside"
      >
        <div class="flex items-center justify-between border-b border-line px-6 py-4">
          <DialogTitle class="text-lg font-semibold text-fg">{{ title }}</DialogTitle>
          <DialogClose class="text-fg-tertiary transition-colors hover:text-fg">
            <X class="size-5" />
          </DialogClose>
        </div>
        <div class="flex-1 overflow-y-auto px-6 py-5">
          <slot />
        </div>
        <div v-if="$slots.footer" class="flex justify-end gap-3 border-t border-line px-6 py-4">
          <slot name="footer" />
        </div>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>

<script setup lang="ts">
import {
  DialogRoot,
  DialogPortal,
  DialogOverlay,
  DialogContent,
  DialogTitle,
  DialogClose,
} from 'reka-ui'
import { X } from 'lucide-vue-next'
import { cn } from '@/lib/utils'

const props = withDefaults(
  defineProps<{
    modelValue: boolean
    title?: string
    width?: string
    closeOnClickOutside?: boolean
  }>(),
  { title: '', width: '600px', closeOnClickOutside: false },
)

defineEmits<{ 'update:modelValue': [value: boolean] }>()

function onInteractOutside(e: Event) {
  if (!props.closeOnClickOutside) e.preventDefault()
}
</script>
