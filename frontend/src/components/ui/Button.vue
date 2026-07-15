<template>
  <button
    :type="nativeType"
    :disabled="disabled || loading"
    :class="cn(buttonVariants({ variant, size }), block && 'w-full', $attrs.class as string)"
  >
    <LoaderCircle v-if="loading" class="size-4 animate-spin" />
    <slot v-else name="icon" />
    <slot />
  </button>
</template>

<script setup lang="ts">
import { cva, type VariantProps } from 'class-variance-authority'
import { LoaderCircle } from 'lucide-vue-next'
import { cn } from '@/lib/utils'

defineOptions({ inheritAttrs: false })

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md font-medium transition-colors ' +
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/40 ' +
    'disabled:opacity-50 disabled:pointer-events-none cursor-pointer select-none',
  {
    variants: {
      variant: {
        primary: 'bg-brand text-brand-fg hover:bg-brand-hover shadow-xs',
        secondary: 'border border-line-strong bg-surface text-fg hover:bg-surface-sunken',
        ghost: 'text-fg hover:bg-surface-sunken',
        text: 'text-brand hover:bg-brand-soft px-2',
        danger: 'bg-danger text-white hover:opacity-90',
        'danger-text': 'text-danger hover:bg-danger-soft px-2',
      },
      size: {
        sm: 'h-8 px-3 text-xs',
        md: 'h-9 px-4 text-sm',
        lg: 'h-11 px-6 text-base',
        icon: 'size-9 p-0',
      },
    },
    defaultVariants: { variant: 'primary', size: 'md' },
  },
)

type ButtonVariants = VariantProps<typeof buttonVariants>

withDefaults(
  defineProps<{
    variant?: ButtonVariants['variant']
    size?: ButtonVariants['size']
    nativeType?: 'button' | 'submit' | 'reset'
    loading?: boolean
    disabled?: boolean
    block?: boolean
  }>(),
  {
    variant: 'primary',
    size: 'md',
    nativeType: 'button',
    loading: false,
    disabled: false,
    block: false,
  },
)
</script>
