<template>
  <span v-bind="rest" :class="cn(badgeVariants({ tone }), $attrs.class as string)">
    <span v-if="dot" class="size-1.5 shrink-0 rounded-full bg-current" />
    <slot>{{ label }}</slot>
  </span>
</template>

<script setup lang="ts">
import { computed, useAttrs } from 'vue'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

defineOptions({ inheritAttrs: false })
const attrs = useAttrs()
const rest = computed(() => {
  const { class: _c, ...others } = attrs
  return others
})

const badgeVariants = cva(
  'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold leading-relaxed whitespace-nowrap',
  {
    variants: {
      tone: {
        neutral: 'border-transparent bg-surface-muted text-fg-secondary',
        brand: 'border-transparent bg-brand-soft text-brand',
        success: 'border-success/30 bg-success-soft text-success',
        warning: 'border-warning/30 bg-warning-soft text-warning',
        danger: 'border-danger/30 bg-danger-soft text-danger',
        info: 'border-info/30 bg-info-soft text-info',
      },
    },
    defaultVariants: { tone: 'neutral' },
  },
)

type BadgeVariants = VariantProps<typeof badgeVariants>

withDefaults(
  defineProps<{ tone?: BadgeVariants['tone']; label?: string; dot?: boolean }>(),
  { tone: 'neutral', dot: false },
)
</script>
