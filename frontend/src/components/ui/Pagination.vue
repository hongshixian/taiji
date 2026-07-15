<template>
  <div v-if="total > 0" class="flex items-center justify-end gap-2 text-sm">
    <span class="mr-2 text-fg-tertiary">共 {{ total }} 条</span>
    <button
      type="button"
      class="flex size-8 items-center justify-center rounded-md border border-line-strong text-fg transition-colors hover:border-brand disabled:opacity-40 disabled:pointer-events-none"
      :disabled="currentPage <= 1"
      @click="go(currentPage - 1)"
    >
      <ChevronLeft class="size-4" />
    </button>
    <button
      v-for="p in pages"
      :key="p"
      type="button"
      :class="cn(
        'flex size-8 items-center justify-center rounded-md border text-sm transition-colors',
        p === currentPage
          ? 'border-brand bg-brand text-brand-fg'
          : 'border-line-strong text-fg hover:border-brand',
      )"
      @click="go(p)"
    >
      {{ p }}
    </button>
    <button
      type="button"
      class="flex size-8 items-center justify-center rounded-md border border-line-strong text-fg transition-colors hover:border-brand disabled:opacity-40 disabled:pointer-events-none"
      :disabled="currentPage >= totalPages"
      @click="go(currentPage + 1)"
    >
      <ChevronRight class="size-4" />
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
import { cn } from '@/lib/utils'

const props = withDefaults(
  defineProps<{ currentPage: number; pageSize: number; total: number }>(),
  { currentPage: 1, pageSize: 10, total: 0 },
)
const emit = defineEmits<{ 'current-change': [page: number] }>()

const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))

// 显示当前页附近最多 7 个页码
const pages = computed(() => {
  const tp = totalPages.value
  const cur = props.currentPage
  const span = 3
  let start = Math.max(1, cur - span)
  let end = Math.min(tp, cur + span)
  if (cur <= span) end = Math.min(tp, 1 + span * 2)
  if (cur > tp - span) start = Math.max(1, tp - span * 2)
  const arr: number[] = []
  for (let i = start; i <= end; i++) arr.push(i)
  return arr
})

function go(p: number) {
  if (p < 1 || p > totalPages.value || p === props.currentPage) return
  emit('current-change', p)
}
</script>
