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

      <!-- 样本预览 -->
      <div v-if="result.samples_preview?.length" class="rounded-md border border-line bg-surface p-6">
        <div class="mb-3 flex items-center justify-between">
          <span class="font-semibold text-fg">样本预览（前 {{ result.samples_preview.length }} 条）</span>
          <UiButton variant="text" size="sm" @click="$emit('view-log')">查看完整日志</UiButton>
        </div>
        <div class="flex flex-col gap-2">
          <details v-for="s in result.samples_preview" :key="s.id" class="rounded-sm border border-line">
            <summary class="flex cursor-pointer items-center gap-3 px-3 py-2 text-sm">
              <span class="font-mono text-fg-secondary">#{{ s.id }}</span>
              <StatusPill :tone="sampleTone(s.score)" :label="String(s.score || '—')" />
            </summary>
            <div class="flex flex-col gap-4 px-3 py-3">
              <div v-for="blk in sampleBlocks(s)" :key="blk.label" :class="blk.error && 'text-danger'">
                <div class="text-xs uppercase tracking-wide text-fg-tertiary">{{ blk.label }}</div>
                <div class="mt-1 whitespace-pre-wrap break-words rounded-sm bg-surface-sunken p-4 font-mono text-xs" :class="blk.error && 'bg-danger-soft'">{{ blk.value }}</div>
              </div>
            </div>
          </details>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { BarChart3 } from 'lucide-vue-next'
import StatusPill from './StatusPill.vue'
import UiAlert from './ui/Alert.vue'
import UiButton from './ui/Button.vue'
import { taskStatusTone as statusTone, taskStatusLabel as statusLabel } from '@/composables/taskStatus'
import type { BenchmarkTask, BenchmarkResult } from '@/api/types'

const props = defineProps<{ task: BenchmarkTask }>()
defineEmits<{ 'view-log': [] }>()

const result = computed<Partial<BenchmarkResult>>(() => props.task.result || {})
const metricEntries = computed(() => Object.entries(result.value.metrics || {}))
const hasResult = computed(() => {
  const r = result.value
  return !!(r.metrics && Object.keys(r.metrics).length) ||
    !!(r.samples_preview && r.samples_preview.length) ||
    (r.total_samples ?? 0) > 0
})

function formatMetric(v: number | string) {
  if (typeof v === 'number') return Number.isInteger(v) ? v.toString() : v.toFixed(4)
  return v
}
function fmtNum(v: number | undefined) {
  if (v == null) return '—'
  return typeof v === 'number' ? v.toLocaleString() : v
}
function sampleTone(score: string): 'success' | 'danger' | 'neutral' {
  const s = String(score || '').toUpperCase()
  if (['C', 'CORRECT', '1', 'TRUE'].includes(s)) return 'success'
  if (['I', 'INCORRECT', '0', 'FALSE'].includes(s)) return 'danger'
  return 'neutral'
}
function sampleBlocks(s: NonNullable<BenchmarkResult['samples_preview']>[number]) {
  const blocks = [
    { label: 'Input', value: s.input || '—', error: false },
    { label: 'Target', value: s.target || '—', error: false },
    { label: 'Output', value: s.output || '—', error: false },
  ]
  if (s.explanation) blocks.push({ label: 'Explanation', value: s.explanation, error: false })
  if (s.error) blocks.push({ label: 'Error', value: s.error, error: true })
  return blocks
}
</script>
