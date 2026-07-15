<template>
  <UiDialog
    :model-value="visible"
    :title="t('benchmark.logDialogTitle')"
    width="760px"
    @update:model-value="$emit('update:visible', $event)"
  >
    <div class="mb-4 flex items-center justify-between gap-4">
      <UiSegmented v-model="levelFilter" :options="levelOptions" />
      <div class="flex items-center gap-3 text-fg-tertiary">
        <span class="text-xs">{{ t('benchmark.logCount', { n: filteredEntries.length }) }}</span>
        <UiButton variant="secondary" size="sm" :loading="loading" @click="refresh">{{ t('common.refresh') }}</UiButton>
      </div>
    </div>

    <div class="min-h-[220px]">
      <UiEmpty v-if="!loading && filteredEntries.length === 0" :description="t('benchmark.noLogs')" />
      <div v-else class="flex flex-col gap-3">
        <article
          v-for="(entry, index) in filteredEntries"
          :key="index"
          class="rounded-md border border-line bg-surface-sunken p-4"
        >
          <header class="mb-2 flex flex-wrap items-center gap-4 text-fg-secondary">
            <UiBadge :tone="levelTone(entry.level)">{{ entry.level || 'INFO' }}</UiBadge>
            <span class="font-mono text-xs">{{ formatTime(entry.ts) }}</span>
            <span class="text-xs">{{ entry.step || '—' }}</span>
            <span class="text-xs">{{ entry.event || '—' }}</span>
            <span class="font-mono text-xs">{{ entry.elapsed_ms ?? 0 }}ms</span>
          </header>
          <div class="text-sm leading-relaxed text-fg">{{ entry.msg || '—' }}</div>
          <pre
            v-if="entry.data && Object.keys(entry.data).length"
            class="mt-2 max-h-44 overflow-auto rounded-sm border border-line bg-surface p-4 font-mono text-xs text-fg"
          >{{ formatJson(entry.data) }}</pre>
        </article>
      </div>
    </div>
  </UiDialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { toast } from '@/lib/toast'
import { getTaskLogs } from '@/api/task'
import type { TaskLogEntry } from '@/api/types'
import UiDialog from './ui/Dialog.vue'
import UiButton from './ui/Button.vue'
import UiBadge from './ui/Badge.vue'
import UiEmpty from './ui/Empty.vue'
import UiSegmented from './ui/SegmentedControl.vue'

const props = defineProps<{
  visible: boolean
  taskId?: number | string | null
}>()
defineEmits<{ 'update:visible': [value: boolean] }>()

const { t } = useI18n()
const loading = ref(false)
const entries = ref<TaskLogEntry[]>([])
const levelFilter = ref<string | number | null>('ALL')

const levelOptions = computed(() => [
  { label: t('common.all'), value: 'ALL' },
  { label: t('benchmark.logInfo'), value: 'INFO' },
  { label: t('benchmark.logWarn'), value: 'WARN' },
  { label: t('benchmark.logError'), value: 'ERROR' },
])

const filteredEntries = computed(() =>
  levelFilter.value === 'ALL'
    ? entries.value
    : entries.value.filter((e) => (e.level || 'INFO') === levelFilter.value),
)

watch(
  () => [props.visible, props.taskId] as const,
  ([vis, tid]) => {
    if (vis && tid != null) fetchLogs(tid)
  },
)

async function refresh() {
  if (props.taskId != null) fetchLogs(props.taskId)
}

async function fetchLogs(id: number | string) {
  loading.value = true
  try {
    const { data } = await getTaskLogs(id)
    entries.value = data.data.items || []
  } catch (err: unknown) {
    const e = err as { response?: { data?: { message?: string } } }
    toast.error(e.response?.data?.message || t('benchmark.loadLogsFailed'))
  } finally {
    loading.value = false
  }
}

function levelTone(level: string): 'info' | 'warning' | 'danger' | 'neutral' {
  return { INFO: 'info', WARN: 'warning', ERROR: 'danger', DEBUG: 'neutral' }[level] as never ?? 'info'
}
function formatTime(value: string | null) {
  return value ? new Date(value).toLocaleString('zh-CN') : '—'
}
function formatJson(value: unknown) {
  return JSON.stringify(value, null, 2)
}
</script>
