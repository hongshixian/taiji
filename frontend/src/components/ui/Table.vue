<template>
  <div class="relative w-full">
    <div class="w-full overflow-x-auto rounded-lg border border-line">
      <table class="w-full border-collapse text-sm">
        <thead>
          <tr class="border-b border-line bg-surface-sunken text-fg-secondary">
            <th v-if="expandable" class="w-10 px-2 py-2.5" />
            <th
              v-for="col in columns"
              :key="col.key"
              :class="cn('px-3 py-2.5 font-semibold', alignClass(col.align), col.fixed === 'right' && 'sticky right-0 bg-surface-sunken')"
              :style="colStyle(col)"
            >
              {{ col.label }}
            </th>
          </tr>
        </thead>
        <tbody>
          <template v-for="(row, idx) in data" :key="rowId(row)">
            <tr
              :class="cn(
                'border-b border-line transition-colors hover:bg-surface-sunken/60',
                stripe && idx % 2 === 1 && 'bg-surface-sunken/40',
              )"
            >
              <td v-if="expandable" class="px-2 py-3 align-middle">
                <button
                  type="button"
                  class="flex size-6 items-center justify-center rounded text-fg-tertiary transition-colors hover:bg-surface-muted hover:text-fg"
                  @click="toggle(row)"
                >
                  <ChevronRight :class="cn('size-4 transition-transform', isExpanded(row) && 'rotate-90')" />
                </button>
              </td>
              <td
                v-for="col in columns"
                :key="col.key"
                :class="cn(
                  'px-3 py-3 align-middle text-fg',
                  alignClass(col.align),
                  col.tooltip && 'max-w-0 truncate',
                  col.fixed === 'right' && 'sticky right-0 bg-surface',
                )"
                :style="colStyle(col)"
                :title="col.tooltip ? String(cellValue(row, col) ?? '') : undefined"
              >
                <slot :name="`cell-${col.key}`" :row="row" :value="cellValue(row, col)" :index="idx">
                  {{ cellValue(row, col) ?? '—' }}
                </slot>
              </td>
            </tr>
            <tr v-if="expandable && isExpanded(row)" :key="`${rowId(row)}-x`" class="border-b border-line bg-surface-sunken/30">
              <td :colspan="columns.length + 1" class="px-6 py-4">
                <slot name="expand" :row="row" />
              </td>
            </tr>
          </template>
          <tr v-if="!data.length && !loading">
            <td :colspan="columns.length + (expandable ? 1 : 0)">
              <slot name="empty">
                <UiEmpty :description="emptyText" />
              </slot>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-if="loading" class="absolute inset-0 flex items-center justify-center bg-surface/60 backdrop-blur-[1px]">
      <UiSpinner :size="28" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ChevronRight } from 'lucide-vue-next'
import { cn } from '@/lib/utils'
import UiEmpty from './Empty.vue'
import UiSpinner from './Spinner.vue'

export interface TableColumn {
  key: string
  label: string
  width?: number
  minWidth?: number
  align?: 'left' | 'center' | 'right'
  fixed?: 'right'
  tooltip?: boolean
  prop?: string // 取值字段，默认 = key
}

const props = withDefaults(
  defineProps<{
    columns: TableColumn[]
    data: any[]
    rowKey?: string
    expandable?: boolean
    expandedKeys?: (string | number)[]
    stripe?: boolean
    loading?: boolean
    emptyText?: string
  }>(),
  {
    rowKey: 'id',
    expandable: false,
    expandedKeys: () => [],
    stripe: false,
    loading: false,
    emptyText: '暂无数据',
  },
)

const emit = defineEmits<{ 'update:expandedKeys': [keys: (string | number)[]] }>()

function rowId(row: any): string | number {
  return row[props.rowKey] as string | number
}
function cellValue(row: any, col: TableColumn) {
  return row[col.prop ?? col.key]
}
function isExpanded(row: any) {
  return props.expandedKeys.includes(rowId(row))
}
function toggle(row: any) {
  const id = rowId(row)
  const next = isExpanded(row)
    ? props.expandedKeys.filter((k) => k !== id)
    : [...props.expandedKeys, id]
  emit('update:expandedKeys', next)
}
function alignClass(a?: string) {
  return a === 'right' ? 'text-right' : a === 'center' ? 'text-center' : 'text-left'
}
function colStyle(col: TableColumn) {
  const s: Record<string, string> = {}
  if (col.width) s.width = `${col.width}px`
  if (col.minWidth) s.minWidth = `${col.minWidth}px`
  return s
}
</script>
