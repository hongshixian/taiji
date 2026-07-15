<template>
  <div class="page-shell flex flex-col gap-8">
    <header class="page-header">
      <span class="page-header__eyebrow t-eyebrow">{{ t('leaderboard.eyebrow') }}</span>
      <div class="flex items-center justify-between gap-6">
        <h1 class="page-header__title">{{ t('leaderboard.title') }}</h1>
      </div>
      <p class="page-header__lede">
        {{ t('leaderboard.lede') }}
      </p>
    </header>

    <!-- Section 筛选 -->
    <div class="flex flex-wrap gap-4">
      <button
        v-for="sec in sectionKeys"
        :key="sec"
        type="button"
        :class="sectionPill(activeSection === sec)"
        @click="activeSection = sec"
      >{{ secLabel(sec) }}</button>
      <button
        type="button"
        :class="sectionPill(activeSection === 'all')"
        @click="activeSection = 'all'"
      >{{ t('common.all') }}</button>
    </div>

    <!-- 各 Section 榜单 -->
    <div v-for="sec in visibleSections" :key="sec" class="flex flex-col gap-5">
      <h2 class="m-0 border-b-2 border-violet-200 pb-4 text-xl font-bold text-fg dark:border-violet-500/30">{{ secLabel(sec) }}</h2>
      <p v-if="secDesc(sec)" class="m-0 max-w-[860px] text-sm leading-relaxed text-fg-secondary">{{ secDesc(sec) }}</p>

      <!-- Benchmark 选择器（按 benchmark 名去重） -->
      <div class="flex flex-wrap gap-3">
        <button
          v-for="bName in sectionBenchmarkNames(sec)"
          :key="bName"
          type="button"
          :class="benchPill(activeBenchName(sec) === bName)"
          @click="setActiveBenchName(sec, bName)"
        >{{ bName }}</button>
      </div>

      <!-- 每个指标一张柱状图 -->
      <div
        v-for="(metric, mIdx) in activeMetrics(sec)"
        :key="metric.key"
        class="flex flex-col gap-3"
      >
        <!-- benchmark 标题 & 描述（仅第一个指标显示） -->
        <div v-if="mIdx === 0" class="flex flex-col gap-2">
          <h3 class="m-0 text-lg font-bold text-fg">{{ activeBenchName(sec) }}</h3>
          <p v-if="benchDesc(activeBenchName(sec))" class="m-0 max-w-[800px] text-sm leading-relaxed text-fg-secondary">{{ benchDesc(activeBenchName(sec)) }}</p>
        </div>
        <div class="flex items-center gap-2 text-sm font-semibold text-fg-secondary">
          {{ metric.metric }}{{ metric.unit ? ' (' + metric.unit + ')' : '' }}
          <span :class="dirBadgeClass(metric.risk_direction)">{{ dirIcon(metric.risk_direction) }}</span>
        </div>
        <div class="rounded-lg border border-line bg-surface px-4 pb-3 pt-4 shadow-xs">
          <v-chart :option="chartOptionForMetric(sec, metric)" :style="{ height: '320px' }" autoresize />
        </div>
      </div>

      <!-- 聚合榜单 -->
      <div class="overflow-hidden rounded-lg border border-line bg-surface shadow-xs">
        <div class="grid grid-cols-[52px_1fr_1fr] border-b border-line bg-surface-sunken px-6 py-3 text-xs font-semibold text-fg-secondary">
          <span>{{ t('leaderboard.rank') }}</span>
          <span>{{ t('leaderboard.model') }}</span>
          <span class="text-violet-600">{{ t('leaderboard.comboScore', { name: activeBenchName(sec) }) }}</span>
        </div>
        <div
          v-for="(row, idx) in aggregatedRankedRows(sec)"
          :key="row.model"
          class="grid grid-cols-[52px_1fr_1fr] items-center border-b border-line px-6 py-4 transition-colors last:border-b-0 hover:bg-surface-sunken"
          :class="idx === 0 && 'bg-violet-50 dark:bg-violet-500/10'"
        >
          <div class="flex items-center">
            <span :class="rankBadgeClass(idx)">{{ idx + 1 }}</span>
          </div>
          <div class="flex items-center pr-4">
            <span class="text-sm font-medium text-fg">{{ row.model }}</span>
          </div>
          <div class="flex items-center gap-4">
            <div v-if="row.avg != null" class="h-1.5 min-w-[60px] flex-1 overflow-hidden rounded-full bg-surface-sunken">
              <div
                class="h-full rounded-full transition-[width] duration-300"
                :class="idx === 0 ? 'bg-violet-600' : 'bg-violet-500'"
                :style="{ width: row.barWidth + '%' }"
              />
            </div>
            <span v-else class="text-sm text-fg-tertiary">—</span>
            <span
              class="min-w-[52px] text-right font-mono text-sm"
              :class="idx === 0 ? 'font-bold text-violet-600 dark:text-violet-300' : 'text-fg'"
            >
              {{ row.avg != null ? fmt(row.avg) : '' }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { cn } from '@/lib/utils'
import rawData from '@/assets/benchmark_data.json'

use([BarChart, GridComponent, TooltipComponent, CanvasRenderer])

interface BenchRow {
  benchmark: string
  metric: string
  unit?: string
  risk_direction: string
  scores: Record<string, number | null>
}
interface MetricItem extends BenchRow {
  key: string
}
interface RankedRow {
  model: string
  avg: number | null
  barWidth: number
}

const { t, locale, messages } = useI18n()

// 文案（section 名 / section 描述 / benchmark 描述）从 i18n 命名空间按 key 读取，
// key 为数据中的原始名称；缺失时回退到原名/空串。图表逻辑与 cssVar 保持不变。
function leaderMsgs(): Record<string, Record<string, string>> {
  const all = messages.value as Record<string, { leaderboard?: Record<string, Record<string, string>> }>
  return (all[locale.value]?.leaderboard ?? {}) as Record<string, Record<string, string>>
}
function secLabel(sec: string): string {
  return leaderMsgs().sectionName?.[sec] ?? sec
}
function secDesc(sec: string): string {
  return leaderMsgs().sectionDesc?.[sec] ?? ''
}
function benchDesc(name: string): string {
  return leaderMsgs().benchmarkDesc?.[name] ?? ''
}

const { models, sections } = rawData as { models: string[]; sections: Record<string, BenchRow[]> }
const sectionKeys = Object.keys(sections)
const activeSection = ref<string>('all')
const activeBenchNameMap = ref<Record<string, string>>({})

const visibleSections = computed<string[]>(() =>
  activeSection.value === 'all' ? sectionKeys : [activeSection.value],
)

// 按 benchmark 名去重，返回有序唯一名称列表
function sectionBenchmarkNames(sec: string): string[] {
  const seen = new Set<string>()
  const names: string[] = []
  for (const r of sections[sec]) {
    if (!seen.has(r.benchmark)) {
      seen.add(r.benchmark)
      names.push(r.benchmark)
    }
  }
  return names
}

function activeBenchName(sec: string): string {
  if (!activeBenchNameMap.value[sec]) {
    activeBenchNameMap.value[sec] = sectionBenchmarkNames(sec)[0] ?? ''
  }
  return activeBenchNameMap.value[sec]
}

function setActiveBenchName(sec: string, name: string) {
  activeBenchNameMap.value[sec] = name
}

// 当前选中 benchmark 的所有指标（去重 benchmark+metric）
function activeMetrics(sec: string): MetricItem[] {
  const name = activeBenchName(sec)
  const seen = new Set<string>()
  return sections[sec]
    .filter((r) => r.benchmark === name)
    .filter((r) => {
      const k = r.benchmark + '|' + r.metric
      if (seen.has(k)) return false
      seen.add(k)
      return true
    })
    .map((r) => ({ ...r, key: r.benchmark + '|' + r.metric }))
}

// 从 CSS 变量读取主题色（支持暗色模式）
function cssVar(name: string, fallback: string): string {
  if (typeof window === 'undefined') return fallback
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return v || fallback
}

// 单指标柱状图配置
function chartOptionForMetric(sec: string, metric: MetricItem): Record<string, unknown> {
  const row = sections[sec].find((r) => r.benchmark + '|' + r.metric === metric.key)
  if (!row) return {}

  const cBar = cssVar('--violet-400', '#a78bfa')
  const cBarNull = cssVar('--border-default', '#e5e7eb')
  const cAxis = cssVar('--fg-tertiary', '#6b7280')
  const cAxisLine = cssVar('--border-subtle', '#e5e7eb')
  const cSplit = cssVar('--border-subtle', '#f3f4f6')
  const cLabel = cssVar('--fg-secondary', '#374151')

  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: { name: string; value: number | null }[]) => {
        const p = params[0]
        if (p.value == null) return `${p.name}<br/><span style="color:${cAxis}">${t('common.noData')}</span>`
        return `${p.name}<br/>${metric.metric}: <b>${fmt(p.value)}</b>${metric.unit ? ' ' + metric.unit : ''}`
      },
    },
    animation: false,
    grid: { left: 16, right: 16, top: 16, bottom: 4, containLabel: true },
    xAxis: {
      type: 'category',
      data: models,
      axisLabel: {
        rotate: 45,
        fontSize: 10,
        interval: 0,
        color: cAxis,
        overflow: 'truncate',
        width: 100,
      },
      axisLine: { lineStyle: { color: cAxisLine } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      axisLabel: { fontSize: 11, color: cAxis },
      splitLine: { lineStyle: { color: cSplit } },
    },
    series: [
      {
        type: 'bar',
        data: models.map((m) => {
          const v = row.scores[m]
          if (v == null) return { value: null, itemStyle: { color: cBarNull, borderRadius: [4, 4, 0, 0] } }
          return {
            value: v,
            itemStyle: { color: cBar, borderRadius: [4, 4, 0, 0] },
          }
        }),
        barMaxWidth: 40,
        label: {
          show: true,
          position: 'top',
          fontSize: 10,
          color: cLabel,
          formatter: (p: { value: number | null }) => (p.value != null ? fmt(p.value) : ''),
        },
      },
    ],
  }
}

// 聚合榜单：当前 benchmark 所有指标标准化后均分排序
function normalizeScore(score: number | null, risk_direction: string): number | null {
  if (score == null) return null
  if (risk_direction === 'higher_worse') return 100 - score
  if (risk_direction === 'distance_from_neutral') return 100 - Math.abs(score - 50)
  return score
}

function aggregatedRankedRows(sec: string): RankedRow[] {
  const metrics = activeMetrics(sec)
  const rows = models.map((model) => {
    const normScores = metrics
      .map((m) => {
        const row = sections[sec].find((r) => r.benchmark + '|' + r.metric === m.key)
        const raw = row ? row.scores[model] : null
        return normalizeScore(raw, m.risk_direction)
      })
      .filter((v): v is number => v != null)
    const avg = normScores.length ? normScores.reduce((a, c) => a + c, 0) / normScores.length : null
    return { model, avg }
  })

  rows.sort((a, b) => {
    if (a.avg == null && b.avg == null) return 0
    if (a.avg == null) return 1
    if (b.avg == null) return -1
    return b.avg - a.avg
  })

  const avgs = rows.map((r) => r.avg).filter((v): v is number => v != null)
  const maxA = Math.max(...avgs)
  const minA = Math.min(...avgs)
  const range = maxA - minA || 1

  return rows.map((r) => ({
    ...r,
    barWidth: r.avg != null ? Math.round(((r.avg - minA) / range) * 85 + 10) : 0,
  }))
}

function fmt(v: number | null): number | string {
  if (typeof v !== 'number') return v ?? ''
  return Number.isInteger(v) ? v : parseFloat(v.toFixed(2))
}

function dirIcon(d: string): string {
  return d === 'higher_worse' ? t('leaderboard.betterLower') : t('leaderboard.betterHigher')
}

// ─── Tailwind class helpers ───
function sectionPill(active: boolean): string {
  return cn(
    'rounded-full border px-6 py-2 text-sm font-medium transition-colors',
    active
      ? 'border-violet-600 bg-violet-600 text-white'
      : 'border-line bg-surface text-fg-secondary hover:border-violet-400 hover:text-fg',
  )
}

function benchPill(active: boolean): string {
  return cn(
    'rounded-md border px-4 py-1.5 text-sm transition-colors',
    active
      ? 'border-violet-500 bg-violet-50 font-semibold text-violet-700 dark:bg-violet-500/15 dark:text-violet-300'
      : 'border-line bg-surface text-fg-secondary hover:border-violet-400 hover:text-fg',
  )
}

function dirBadgeClass(d: string): string {
  const map: Record<string, string> = {
    lower_worse: 'bg-success-soft text-success',
    higher_worse: 'bg-info-soft text-info',
    threshold_only: 'bg-warning-soft text-warning',
    distance_from_neutral: 'bg-surface-sunken text-fg-tertiary',
  }
  return cn('rounded-sm px-1.5 py-px text-xs', map[d] ?? 'bg-surface-sunken text-fg-tertiary')
}

function rankBadgeClass(idx: number): string {
  const base = 'inline-flex size-[26px] items-center justify-center rounded-full text-xs font-bold'
  if (idx === 0) return cn(base, 'bg-[#f6c94e] text-[#7a5700]')
  if (idx === 1) return cn(base, 'bg-[#c0c0c0] text-[#444]')
  if (idx === 2) return cn(base, 'bg-[#cd7f32] text-white')
  return cn(base, 'bg-surface-sunken text-fg-tertiary')
}
</script>
