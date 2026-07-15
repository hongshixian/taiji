<template>
  <div class="flex flex-col gap-6 py-2">
    <!-- 失败且有错误 -->
    <UiAlert
      v-if="task.status === 'failed' && task.error_message"
      type="danger"
      :title="t('benchmark.execFailed')"
    >
      <pre class="mt-2 max-h-40 overflow-auto whitespace-pre-wrap break-words font-mono text-xs">{{ task.error_message }}</pre>
    </UiAlert>

    <!-- 无结果 -->
    <div v-if="!hasResult" class="flex flex-col items-center gap-4 py-10 text-center text-fg-tertiary">
      <BarChart3 class="size-7" />
      <span>{{ task.status === 'failed' ? t('benchmark.noResultFailed') : t('benchmark.noResultYet') }}</span>
    </div>

    <template v-else>
      <!-- 概览卡片 -->
      <div class="grid grid-cols-[repeat(auto-fit,minmax(240px,1fr))] gap-5">
        <div class="rounded-md border border-line bg-surface-sunken p-6">
          <div class="mb-5 font-semibold text-fg">{{ t('benchmark.mainMetrics') }}</div>
          <div v-if="metricEntries.length" class="flex flex-col gap-3">
            <div v-for="[k, v] in metricEntries" :key="k" class="flex items-center justify-between gap-4">
              <span class="font-mono text-sm text-fg-secondary">{{ k }}</span>
              <span class="font-mono font-semibold text-fg">{{ formatMetric(v) }}</span>
            </div>
          </div>
          <div v-else class="text-sm text-fg-tertiary">{{ t('benchmark.noMetrics') }}</div>
        </div>

        <div class="rounded-md border border-line bg-surface-sunken p-6">
          <div class="mb-5 font-semibold text-fg">{{ t('benchmark.sampleStats') }}</div>
          <div class="flex flex-col gap-3">
            <div class="flex items-center justify-between"><span class="text-sm text-fg-secondary">{{ t('benchmark.sampleTotal') }}</span><span class="font-mono font-semibold text-fg">{{ result.total_samples ?? '—' }}</span></div>
            <div class="flex items-center justify-between"><span class="text-sm text-fg-secondary">{{ t('benchmark.sampleCompleted') }}</span><span class="font-mono font-semibold text-fg">{{ result.completed_samples ?? '—' }}</span></div>
            <div class="flex items-center justify-between"><span class="text-sm text-fg-secondary">{{ t('benchmark.sampleFailed') }}</span><span class="font-mono font-semibold" :class="result.failed_samples ? 'text-danger' : 'text-fg'">{{ result.failed_samples ?? 0 }}</span></div>
            <div class="flex items-center justify-between"><span class="text-sm text-fg-secondary">{{ t('common.status') }}</span><StatusPill :tone="statusTone(result.status || task.status)" :label="statusLabel(result.status || task.status)" /></div>
          </div>
        </div>

        <div class="rounded-md border border-line bg-surface-sunken p-6">
          <div class="mb-5 font-semibold text-fg">{{ t('benchmark.tokenUsage') }}</div>
          <div class="flex flex-col gap-3">
            <div class="flex items-center justify-between"><span class="text-sm text-fg-secondary">{{ t('benchmark.tokenInput') }}</span><span class="font-mono font-semibold text-fg">{{ fmtNum(result.model_usage?.input_tokens) }}</span></div>
            <div class="flex items-center justify-between"><span class="text-sm text-fg-secondary">{{ t('benchmark.tokenOutput') }}</span><span class="font-mono font-semibold text-fg">{{ fmtNum(result.model_usage?.output_tokens) }}</span></div>
            <div class="flex items-center justify-between"><span class="text-sm text-fg-secondary">{{ t('benchmark.tokenTotal') }}</span><span class="font-mono font-semibold text-fg">{{ fmtNum(result.model_usage?.total_tokens) }}</span></div>
            <div class="flex items-center justify-between"><span class="text-sm text-fg-secondary">{{ t('benchmark.engine') }}</span><span class="font-mono font-semibold text-fg">{{ result.engine || '—' }}</span></div>
          </div>
        </div>
      </div>

      <!-- 元信息 -->
      <div class="flex flex-wrap gap-x-8 gap-y-4 rounded-md border border-line bg-surface px-6 py-4">
        <div class="flex items-center gap-3 text-sm"><span class="text-fg-tertiary">Suite</span><span class="font-mono">{{ task.benchmark_suite }}</span></div>
        <div class="flex items-center gap-3 text-sm"><span class="text-fg-tertiary">{{ t('benchmark.metaTarget') }}</span><span>{{ task.target_model?.display_name || '—' }}</span></div>
        <div class="flex items-center gap-3 text-sm"><span class="text-fg-tertiary">{{ t('benchmark.metaJudge') }}</span><span>{{ task.judge_model?.display_name || t('common.none') }}</span></div>
      </div>

      <!-- 样本网格（contribution-graph 风格） -->
      <div v-if="gridCells.length" class="rounded-md border border-line bg-surface p-6">
        <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
          <span class="font-semibold text-fg">{{ t('benchmark.sampleDistribution', { n: gridCells.length }) }}</span>
          <div class="flex items-center gap-4">
            <div class="flex items-center gap-4 text-xs text-fg-secondary">
              <span class="flex items-center gap-1.5"><i class="size-3 rounded-[3px]" style="background:var(--color-success-fg)" />{{ t('benchmark.sampleSuccess') }} {{ counts.success }}</span>
              <span class="flex items-center gap-1.5"><i class="size-3 rounded-[3px]" style="background:var(--color-danger-fg)" />{{ t('benchmark.sampleError') }} {{ counts.error }}</span>
              <span class="flex items-center gap-1.5"><i class="size-3 rounded-[3px]" style="background:var(--color-warning-fg)" />{{ t('benchmark.sampleNone') }} {{ counts.none }}</span>
            </div>
            <UiButton variant="text" size="sm" @click="$emit('view-log')">{{ t('benchmark.viewFullLog') }}</UiButton>
          </div>
        </div>
        <div class="flex flex-wrap gap-[3px]">
          <button
            v-for="(cell, i) in gridCells"
            :key="cell.id ?? i"
            type="button"
            :class="cn(
              'size-3.5 rounded-[3px] transition-transform hover:scale-125 hover:ring-2 hover:ring-brand/40 focus:outline-none',
              cellClass(cell.status),
            )"
            :title="`#${cell.id} · ${statusText(cell.status)}`"
            @click="openSample(cell)"
          />
        </div>
        <p v-if="!hasDetailForAll" class="mt-3 text-xs text-fg-tertiary">
          {{ t('benchmark.sampleLimitHint', { n: detailCount }) }}
        </p>
      </div>
    </template>

    <!-- 样本详情弹窗 -->
    <UiDialog v-model="sampleDialogOpen" :title="t('benchmark.sampleDialogTitle', { id: activeSample?.id ?? '' })" width="640px">
      <div v-if="activeSample" class="flex flex-col gap-4">
        <div class="flex items-center gap-3">
          <StatusPill :tone="cellTone(activeSample.status)" :label="statusText(activeSample.status)" />
          <span class="font-mono text-sm text-fg-tertiary">#{{ activeSample.id }}</span>
        </div>
        <template v-if="activeSample.detail">
          <div v-for="blk in sampleBlocks(activeSample.detail)" :key="blk.label" :class="blk.error && 'text-danger'">
            <div class="text-xs uppercase tracking-wide text-fg-tertiary">{{ blk.label }}</div>
            <div class="mt-1 max-h-52 overflow-auto whitespace-pre-wrap break-words rounded-sm bg-surface-sunken p-4 font-mono text-xs" :class="blk.error && 'bg-danger-soft'">{{ blk.value }}</div>
          </div>
        </template>
        <div v-else class="rounded-sm bg-surface-sunken p-4 text-sm text-fg-secondary">
          {{ t('benchmark.sampleNoDetailPrefix') }}
          <button type="button" class="text-brand hover:underline" @click="sampleDialogOpen = false; $emit('view-log')">{{ t('benchmark.viewFullLog') }}</button>{{ t('benchmark.sampleNoDetailSuffix') }}
        </div>
      </div>
    </UiDialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { BarChart3 } from 'lucide-vue-next'
import StatusPill from './StatusPill.vue'
import UiAlert from './ui/Alert.vue'
import UiButton from './ui/Button.vue'
import UiDialog from './ui/Dialog.vue'
import { cn } from '@/lib/utils'
import { taskStatusTone as statusTone, taskStatusLabel as statusLabel } from '@/composables/taskStatus'
import type { BenchmarkTask, BenchmarkResult } from '@/api/types'

type SampleStatus = 'success' | 'error' | 'none'
type SampleDetail = NonNullable<BenchmarkResult['samples_preview']>[number]
interface GridCell {
  id: string | number
  status: SampleStatus
  detail?: SampleDetail
}

const props = defineProps<{ task: BenchmarkTask }>()
defineEmits<{ 'view-log': [] }>()
const { t } = useI18n()

const result = computed<Partial<BenchmarkResult>>(() => props.task.result || {})
const metricEntries = computed(() => Object.entries(result.value.metrics || {}))
const hasResult = computed(() => {
  const r = result.value
  return !!(r.metrics && Object.keys(r.metrics).length) ||
    !!(r.samples_preview && r.samples_preview.length) ||
    !!(r.sample_grid && r.sample_grid.length) ||
    (r.total_samples ?? 0) > 0
})

// 详情映射（前 N 条带完整文本）
const detailMap = computed(() => {
  const m = new Map<string, SampleDetail>()
  for (const s of result.value.samples_preview || []) m.set(String(s.id), s)
  return m
})
const detailCount = computed(() => (result.value.samples_preview || []).length)

// 网格单元：优先用 sample_grid（全部样本）；旧数据无 grid 时回退到 samples_preview
const gridCells = computed<GridCell[]>(() => {
  const grid = result.value.sample_grid
  if (grid && grid.length) {
    return grid.map((g) => ({
      id: g.id,
      status: g.status,
      detail: detailMap.value.get(String(g.id)),
    }))
  }
  return (result.value.samples_preview || []).map((s) => ({
    id: s.id,
    status: detailStatus(s),
    detail: s,
  }))
})

const hasDetailForAll = computed(() => gridCells.value.every((c) => c.detail))

const counts = computed(() => {
  let success = 0, error = 0, none = 0
  for (const c of gridCells.value) {
    if (c.status === 'success') success++
    else if (c.status === 'error') error++
    else none++
  }
  return { success, error, none }
})

const sampleDialogOpen = ref(false)
const activeSample = ref<GridCell | null>(null)
function openSample(cell: GridCell) {
  activeSample.value = cell
  sampleDialogOpen.value = true
}

// 只看是否拿到结果，不看答对答错
function detailStatus(s: SampleDetail): SampleStatus {
  if (s.error) return 'error'
  if (s.score || s.output) return 'success'
  return 'none'
}

// 执行成功=绿，执行失败(报错)=红，未执行=黄
function cellClass(status: SampleStatus): string {
  if (status === 'success') return 'bg-[var(--color-success-fg)]'
  if (status === 'error') return 'bg-[var(--color-danger-fg)]'
  return 'bg-[var(--color-warning-fg)]'
}
function cellTone(status: SampleStatus): 'success' | 'danger' | 'warning' {
  if (status === 'success') return 'success'
  if (status === 'error') return 'danger'
  return 'warning'
}
function statusText(status: SampleStatus): string {
  return { success: t('benchmark.sampleSuccess'), error: t('benchmark.sampleError'), none: t('benchmark.sampleNone') }[status]
}

function formatMetric(v: number | string) {
  if (typeof v === 'number') return Number.isInteger(v) ? v.toString() : v.toFixed(4)
  return v
}
function fmtNum(v: number | undefined) {
  if (v == null) return '—'
  return typeof v === 'number' ? v.toLocaleString() : v
}
function sampleBlocks(s: SampleDetail) {
  const blocks = [
    { label: 'Input', value: s.input || '—', error: false },
    { label: 'Target', value: s.target || '—', error: false },
    { label: 'Output', value: s.output || '—', error: false },
  ]
  if (s.score) blocks.push({ label: 'Score', value: String(s.score), error: false })
  if (s.explanation) blocks.push({ label: 'Explanation', value: s.explanation, error: false })
  if (s.error) blocks.push({ label: 'Error', value: s.error, error: true })
  return blocks
}
</script>
