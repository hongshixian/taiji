<template>
  <div class="flex flex-col gap-6 py-2">
    <!-- 失败且有错误 -->
    <UiAlert
      v-if="task.status === 'failed' && task.error_message"
      type="danger"
      title="评测执行失败"
    >
      <pre class="mt-2 max-h-40 overflow-auto whitespace-pre-wrap break-words font-mono text-xs">{{ task.error_message }}</pre>
    </UiAlert>

    <!-- 无结果 -->
    <div v-if="!hasResult" class="flex flex-col items-center gap-4 py-10 text-center text-fg-tertiary">
      <BarChart3 class="size-7" />
      <span>{{ task.status === 'failed' ? '任务失败，未产出结果' : '任务尚未产出结果' }}</span>
    </div>

    <template v-else>
      <!-- 概览卡片 -->
      <div class="grid grid-cols-[repeat(auto-fit,minmax(240px,1fr))] gap-5">
        <div class="rounded-md border border-line bg-surface-sunken p-6">
          <div class="mb-5 font-semibold text-fg">主要指标</div>
          <div v-if="metricEntries.length" class="flex flex-col gap-3">
            <div v-for="[k, v] in metricEntries" :key="k" class="flex items-center justify-between gap-4">
              <span class="font-mono text-sm text-fg-secondary">{{ k }}</span>
              <span class="font-mono font-semibold text-fg">{{ formatMetric(v) }}</span>
            </div>
          </div>
          <div v-else class="text-sm text-fg-tertiary">暂无指标</div>
        </div>

        <div class="rounded-md border border-line bg-surface-sunken p-6">
          <div class="mb-5 font-semibold text-fg">样本统计</div>
          <div class="flex flex-col gap-3">
            <div class="flex items-center justify-between"><span class="text-sm text-fg-secondary">总数</span><span class="font-mono font-semibold text-fg">{{ result.total_samples ?? '—' }}</span></div>
            <div class="flex items-center justify-between"><span class="text-sm text-fg-secondary">已完成</span><span class="font-mono font-semibold text-fg">{{ result.completed_samples ?? '—' }}</span></div>
            <div class="flex items-center justify-between"><span class="text-sm text-fg-secondary">失败</span><span class="font-mono font-semibold" :class="result.failed_samples ? 'text-danger' : 'text-fg'">{{ result.failed_samples ?? 0 }}</span></div>
            <div class="flex items-center justify-between"><span class="text-sm text-fg-secondary">状态</span><StatusPill :tone="statusTone(result.status || task.status)" :label="statusLabel(result.status || task.status)" /></div>
          </div>
        </div>

        <div class="rounded-md border border-line bg-surface-sunken p-6">
          <div class="mb-5 font-semibold text-fg">Token 消耗</div>
          <div class="flex flex-col gap-3">
            <div class="flex items-center justify-between"><span class="text-sm text-fg-secondary">输入</span><span class="font-mono font-semibold text-fg">{{ fmtNum(result.model_usage?.input_tokens) }}</span></div>
            <div class="flex items-center justify-between"><span class="text-sm text-fg-secondary">输出</span><span class="font-mono font-semibold text-fg">{{ fmtNum(result.model_usage?.output_tokens) }}</span></div>
            <div class="flex items-center justify-between"><span class="text-sm text-fg-secondary">合计</span><span class="font-mono font-semibold text-fg">{{ fmtNum(result.model_usage?.total_tokens) }}</span></div>
            <div class="flex items-center justify-between"><span class="text-sm text-fg-secondary">引擎</span><span class="font-mono font-semibold text-fg">{{ result.engine || '—' }}</span></div>
          </div>
        </div>
      </div>

      <!-- 元信息 -->
      <div class="flex flex-wrap gap-x-8 gap-y-4 rounded-md border border-line bg-surface px-6 py-4">
        <div class="flex items-center gap-3 text-sm"><span class="text-fg-tertiary">Suite</span><span class="font-mono">{{ task.benchmark_suite }}</span></div>
        <div class="flex items-center gap-3 text-sm"><span class="text-fg-tertiary">被测</span><span>{{ task.target_model?.display_name || '—' }}</span></div>
        <div class="flex items-center gap-3 text-sm"><span class="text-fg-tertiary">评委</span><span>{{ task.judge_model?.display_name || '（无）' }}</span></div>
      </div>

      <!-- 样本网格（contribution-graph 风格） -->
      <div v-if="gridCells.length" class="rounded-md border border-line bg-surface p-6">
        <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
          <span class="font-semibold text-fg">样本分布（{{ gridCells.length }} 条）</span>
          <div class="flex items-center gap-4">
            <div class="flex items-center gap-4 text-xs text-fg-secondary">
              <span class="flex items-center gap-1.5"><i class="size-3 rounded-[3px]" style="background:var(--color-success-fg)" />成功 {{ counts.correct }}</span>
              <span class="flex items-center gap-1.5"><i class="size-3 rounded-[3px]" style="background:var(--color-danger-fg)" />失败 {{ counts.fail }}</span>
              <span class="flex items-center gap-1.5"><i class="size-3 rounded-[3px] border border-line bg-surface" />未执行 {{ counts.none }}</span>
            </div>
            <UiButton variant="text" size="sm" @click="$emit('view-log')">查看完整日志</UiButton>
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
          提示：仅前 {{ detailCount }} 条样本可查看完整内容，其余方块仅展示执行状态。
        </p>
      </div>
    </template>

    <!-- 样本详情弹窗 -->
    <UiDialog v-model="sampleDialogOpen" :title="`样本 #${activeSample?.id ?? ''}`" width="640px">
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
          该样本超出预览范围，仅记录了执行状态。完整内容请
          <button type="button" class="text-brand hover:underline" @click="sampleDialogOpen = false; $emit('view-log')">查看完整日志</button>。
        </div>
      </div>
    </UiDialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { BarChart3 } from 'lucide-vue-next'
import StatusPill from './StatusPill.vue'
import UiAlert from './ui/Alert.vue'
import UiButton from './ui/Button.vue'
import UiDialog from './ui/Dialog.vue'
import { cn } from '@/lib/utils'
import { taskStatusTone as statusTone, taskStatusLabel as statusLabel } from '@/composables/taskStatus'
import type { BenchmarkTask, BenchmarkResult } from '@/api/types'

type SampleStatus = 'correct' | 'incorrect' | 'error' | 'none'
type SampleDetail = NonNullable<BenchmarkResult['samples_preview']>[number]
interface GridCell {
  id: string | number
  status: SampleStatus
  detail?: SampleDetail
}

const props = defineProps<{ task: BenchmarkTask }>()
defineEmits<{ 'view-log': [] }>()

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
  let correct = 0, fail = 0, none = 0
  for (const c of gridCells.value) {
    if (c.status === 'correct') correct++
    else if (c.status === 'incorrect' || c.status === 'error') fail++
    else none++
  }
  return { correct, fail, none }
})

const sampleDialogOpen = ref(false)
const activeSample = ref<GridCell | null>(null)
function openSample(cell: GridCell) {
  activeSample.value = cell
  sampleDialogOpen.value = true
}

function detailStatus(s: SampleDetail): SampleStatus {
  if (s.error) return 'error'
  const k = String(s.score || '').trim().toUpperCase()
  if (['C', 'CORRECT', '1', 'TRUE'].includes(k)) return 'correct'
  if (['I', 'INCORRECT', '0', 'FALSE'].includes(k)) return 'incorrect'
  const n = Number(k)
  if (!Number.isNaN(n)) return n > 0 ? 'correct' : 'incorrect'
  return 'none'
}

// 成功=绿，失败(答错/执行错)=红，未执行=白
function cellClass(status: SampleStatus): string {
  if (status === 'correct') return 'bg-[var(--color-success-fg)]'
  if (status === 'incorrect' || status === 'error') return 'bg-[var(--color-danger-fg)]'
  return 'border border-line bg-surface'
}
function cellTone(status: SampleStatus): 'success' | 'danger' | 'neutral' {
  if (status === 'correct') return 'success'
  if (status === 'incorrect' || status === 'error') return 'danger'
  return 'neutral'
}
function statusText(status: SampleStatus): string {
  return { correct: '成功', incorrect: '失败', error: '执行错误', none: '未执行' }[status]
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
