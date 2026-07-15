<template>
  <PopoverRoot :open="open" @update:open="onOpenChange">
    <PopoverTrigger as-child>
      <button
        type="button"
        :disabled="disabled"
        :class="cn(
          'inline-flex h-9 w-full items-center justify-between gap-2 rounded-md border bg-surface px-3 text-left',
          'text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-brand/30',
          open ? 'border-brand' : 'border-line-strong hover:border-brand',
          disabled && 'opacity-60 pointer-events-none',
        )"
      >
        <span :class="selectedLabel ? 'text-fg truncate' : 'text-fg-tertiary truncate'">
          {{ selectedLabel || placeholder }}
        </span>
        <span class="flex shrink-0 items-center gap-1">
          <X
            v-if="clearable && modelValue != null && modelValue !== ''"
            class="size-3.5 text-fg-tertiary hover:text-fg"
            @click.stop="clear"
          />
          <ChevronDown class="size-4 text-fg-tertiary" />
        </span>
      </button>
    </PopoverTrigger>
    <PopoverPortal>
      <PopoverContent
        align="start"
        :side-offset="4"
        class="z-[60] w-[var(--reka-popover-trigger-width)] overflow-hidden rounded-md border border-line bg-surface-raised shadow-lg"
      >
        <div v-if="filterable" class="border-b border-line p-2">
          <input
            ref="filterInput"
            v-model="query"
            :placeholder="filterPlaceholder"
            class="w-full rounded-sm bg-surface-sunken px-2 py-1.5 text-sm text-fg placeholder:text-fg-tertiary focus:outline-none"
          />
        </div>
        <div class="max-h-64 overflow-y-auto p-1">
          <template v-for="grp in filteredGroups" :key="grp.label ?? '_'">
            <div v-if="grp.label && grp.options.length" class="px-2 py-1.5 text-xs font-semibold text-fg-tertiary">
              {{ grp.label }}
            </div>
            <button
              v-for="opt in grp.options"
              :key="String(opt.value)"
              type="button"
              :disabled="opt.disabled"
              :class="cn(
                'flex w-full cursor-pointer items-center gap-2 rounded-sm px-2 py-1.5 text-left text-sm text-fg',
                'hover:bg-brand-soft disabled:cursor-not-allowed disabled:opacity-40',
                isSelected(opt) && 'bg-brand-soft font-medium',
              )"
              @click="pick(opt)"
            >
              <Check :class="cn('size-4 shrink-0', isSelected(opt) ? 'text-brand' : 'invisible')" />
              <span class="flex-1 truncate">{{ opt.label }}</span>
              <span v-if="opt.badge" class="font-mono text-xs text-fg-tertiary">{{ opt.badge }}</span>
            </button>
          </template>
          <div v-if="isEmpty" class="px-3 py-6 text-center text-sm text-fg-tertiary">无匹配项</div>
        </div>
      </PopoverContent>
    </PopoverPortal>
  </PopoverRoot>
</template>

<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { PopoverRoot, PopoverTrigger, PopoverPortal, PopoverContent } from 'reka-ui'
import { ChevronDown, Check, X } from 'lucide-vue-next'
import { cn } from '@/lib/utils'

export interface SelectOption {
  label: string
  value: string | number
  disabled?: boolean
  badge?: string
}
export interface SelectGroupDef {
  label?: string
  options: SelectOption[]
}

const props = withDefaults(
  defineProps<{
    modelValue?: string | number | null
    placeholder?: string
    filterPlaceholder?: string
    options?: SelectOption[]
    groups?: SelectGroupDef[]
    filterable?: boolean
    clearable?: boolean
    disabled?: boolean
  }>(),
  {
    placeholder: '请选择',
    filterPlaceholder: '搜索…',
    options: () => [],
    groups: () => [],
    filterable: false,
    clearable: false,
    disabled: false,
  },
)

const emit = defineEmits<{ 'update:modelValue': [value: string | number | null] }>()

const open = ref(false)
const query = ref('')
const filterInput = ref<HTMLInputElement | null>(null)

const baseGroups = computed<SelectGroupDef[]>(() =>
  props.groups.length ? props.groups : [{ options: props.options }],
)

const allOptions = computed<SelectOption[]>(() => baseGroups.value.flatMap((g) => g.options))

const selectedLabel = computed(() => {
  const found = allOptions.value.find((o) => o.value === props.modelValue)
  return found?.label ?? ''
})

const filteredGroups = computed<SelectGroupDef[]>(() => {
  if (!props.filterable || !query.value.trim()) return baseGroups.value
  const q = query.value.trim().toLowerCase()
  return baseGroups.value
    .map((g) => ({ label: g.label, options: g.options.filter((o) => o.label.toLowerCase().includes(q)) }))
    .filter((g) => g.options.length)
})

const isEmpty = computed(() => filteredGroups.value.every((g) => !g.options.length))

function isSelected(opt: SelectOption) {
  return opt.value === props.modelValue
}

function onOpenChange(v: boolean) {
  open.value = v
  if (v && props.filterable) {
    query.value = ''
    nextTick(() => filterInput.value?.focus())
  }
}

function pick(opt: SelectOption) {
  if (opt.disabled) return
  emit('update:modelValue', opt.value)
  open.value = false
}

function clear() {
  emit('update:modelValue', null)
}
</script>
