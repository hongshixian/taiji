<template>
  <div class="page-shell leaderboard">
    <header class="page-header">
      <span class="page-header__eyebrow t-eyebrow">测评榜单</span>
      <div class="page-header__row">
        <h1 class="page-header__title">模型测评榜单</h1>
      </div>
      <p class="page-header__lede">
        汇总各模型在安全性 Benchmark 上的测评结果，从优到劣排列。数据来源：静态基准测评数据集。
      </p>
    </header>

    <!-- Section 筛选 -->
    <div class="section-filters">
      <button
        v-for="sec in sectionKeys"
        :key="sec"
        class="section-btn"
        :class="{ 'section-btn--active': activeSection === sec }"
        @click="activeSection = sec"
      >{{ sec }}</button>
      <button
        class="section-btn"
        :class="{ 'section-btn--active': activeSection === 'all' }"
        @click="activeSection = 'all'"
      >全部</button>
    </div>

    <!-- 各 Section 榜单 -->
    <div v-for="sec in visibleSections" :key="sec" class="board-section">
      <h2 class="board-section__title">{{ sec }}</h2>

      <div class="table-wrap">
        <table class="lb-table">
          <thead>
            <tr>
              <th class="col-rank">#</th>
              <th class="col-model">模型</th>
              <th
                v-for="b in sectionBenchmarks(sec)"
                :key="b.key"
                class="col-bench"
                :title="b.metric + (b.unit ? ' (' + b.unit + ')' : '') + '\n方向：' + dirLabel(b.risk_direction)"
              >
                <span class="bench-name">{{ b.benchmark }}</span>
                <span class="bench-meta">{{ b.metric }}</span>
                <span class="bench-dir" :data-dir="b.risk_direction">{{ dirIcon(b.risk_direction) }}</span>
              </th>
              <th class="col-avg">均分</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(row, idx) in rankedRows(sec)"
              :key="row.model"
              :class="{ 'row--top': idx === 0 }"
            >
              <td class="col-rank">
                <span class="rank-badge" :data-rank="idx < 3 ? idx + 1 : 'rest'">{{ idx + 1 }}</span>
              </td>
              <td class="col-model">
                <span class="model-name">{{ row.model }}</span>
              </td>
              <td
                v-for="b in sectionBenchmarks(sec)"
                :key="b.key"
                class="col-bench"
                :class="cellClass(row.model, sec, b)"
              >
                <span v-if="row.scores[b.key] != null">{{ fmt(row.scores[b.key]) }}</span>
                <span v-else class="null-val">—</span>
              </td>
              <td class="col-avg">
                <span class="avg-val">{{ row.avg != null ? row.avg.toFixed(1) : '—' }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import rawData from '../assets/benchmark_data.json'

const { models, sections } = rawData
const sectionKeys = Object.keys(sections)
const activeSection = ref('all')

const visibleSections = computed(() =>
  activeSection.value === 'all' ? sectionKeys : [activeSection.value]
)

// 每个 section 的 benchmark 列表（去重，用 benchmark+metric 作 key）
function sectionBenchmarks(sec) {
  const seen = new Set()
  return sections[sec].filter(r => {
    const k = r.benchmark + '|' + r.metric
    if (seen.has(k)) return false
    seen.add(k)
    return true
  }).map(r => ({ ...r, key: r.benchmark + '|' + r.metric }))
}

// 针对 lower_worse（高分好）/ higher_worse（低分好）统一成"高分=好"标准
function normalizeScore(score, risk_direction) {
  if (score == null) return null
  if (risk_direction === 'higher_worse') return 100 - score
  return score
}

// 每个 section 按标准化均分排序的模型行
function rankedRows(sec) {
  const benches = sectionBenchmarks(sec)
  const rows = models.map(model => {
    const scoreMap = {}
    benches.forEach(b => {
      // 找到对应行的分数
      const row = sections[sec].find(r => r.benchmark + '|' + r.metric === b.key)
      scoreMap[b.key] = row ? row.scores[model] : null
    })
    const normalized = benches.map(b => normalizeScore(scoreMap[b.key], b.risk_direction)).filter(v => v != null)
    const avg = normalized.length ? normalized.reduce((a, c) => a + c, 0) / normalized.length : null
    return { model, scores: scoreMap, avg }
  })
  return rows.sort((a, b) => (b.avg ?? -Infinity) - (a.avg ?? -Infinity))
}

// 找每列（benchmark）的最佳原始分（考虑 risk_direction）
function bestScore(sec, b) {
  const row = sections[sec].find(r => r.benchmark + '|' + r.metric === b.key)
  if (!row) return null
  const vals = models.map(m => row.scores[m]).filter(v => v != null)
  if (!vals.length) return null
  return b.risk_direction === 'higher_worse' ? Math.min(...vals) : Math.max(...vals)
}

function cellClass(model, sec, b) {
  const row = sections[sec].find(r => r.benchmark + '|' + r.metric === b.key)
  if (!row) return ''
  const score = row.scores[model]
  if (score == null) return ''
  const best = bestScore(sec, b)
  return score === best ? 'cell--best' : ''
}

function fmt(v) {
  return typeof v === 'number' ? (Number.isInteger(v) ? v : v.toFixed(1)) : v
}

function dirLabel(d) {
  return d === 'higher_worse' ? '越低越好' : '越高越好'
}
function dirIcon(d) {
  return d === 'higher_worse' ? '↓优' : '↑优'
}
</script>

<style scoped>
.leaderboard {
  display: flex;
  flex-direction: column;
  gap: var(--space-9);
}

.page-header__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-7);
}

/* ─── 筛选按钮 ─── */
.section-filters {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-4);
}
.section-btn {
  padding: var(--space-3) var(--space-6);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-full);
  background: var(--bg-surface);
  color: var(--fg-secondary);
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  cursor: pointer;
  transition: background var(--dur-base), border-color var(--dur-base), color var(--dur-base);
}
.section-btn:hover {
  border-color: var(--violet-400);
  color: var(--fg-primary);
}
.section-btn--active {
  background: var(--violet-600);
  border-color: var(--violet-600);
  color: #fff;
}

/* ─── Section 标题 ─── */
.board-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}
.board-section__title {
  margin: 0;
  font-size: var(--text-xl);
  font-weight: var(--weight-bold);
  color: var(--fg-primary);
  padding-bottom: var(--space-4);
  border-bottom: 2px solid var(--violet-200);
}
[data-theme="dark"] .board-section__title,
html.dark .board-section__title {
  border-bottom-color: rgba(143, 114, 208, 0.3);
}

/* ─── 表格容器 ─── */
.table-wrap {
  overflow-x: auto;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xs);
}

/* ─── 榜单表格 ─── */
.lb-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
  background: var(--bg-surface);
}
.lb-table thead tr {
  background: var(--bg-surface-sunken);
  border-bottom: 1px solid var(--border-subtle);
}
.lb-table th {
  padding: var(--space-4) var(--space-5);
  text-align: center;
  font-weight: var(--weight-semibold);
  color: var(--fg-secondary);
  white-space: nowrap;
  font-size: var(--text-xs);
  vertical-align: bottom;
}
.lb-table th.col-model { text-align: left; }
.lb-table th.col-rank { width: 40px; }
.lb-table th.col-avg { color: var(--violet-600); }

.lb-table tbody tr {
  border-bottom: 1px solid var(--border-subtle);
  transition: background var(--dur-base);
}
.lb-table tbody tr:last-child { border-bottom: none; }
.lb-table tbody tr:hover { background: var(--state-hover); }
.lb-table tbody tr.row--top { background: var(--violet-50); }
[data-theme="dark"] .lb-table tbody tr.row--top,
html.dark .lb-table tbody tr.row--top {
  background: rgba(109, 79, 186, 0.1);
}

.lb-table td {
  padding: var(--space-4) var(--space-5);
  text-align: center;
  color: var(--fg-primary);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
}
.lb-table td.col-model { text-align: left; font-family: inherit; }
.lb-table td.col-rank { text-align: center; font-family: inherit; }

/* ─── 排名徽章 ─── */
.rank-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px; height: 24px;
  border-radius: var(--radius-full);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  background: var(--bg-surface-sunken);
  color: var(--fg-tertiary);
}
.rank-badge[data-rank='1'] { background: #f6c94e; color: #7a5700; }
.rank-badge[data-rank='2'] { background: #c0c0c0; color: #444; }
.rank-badge[data-rank='3'] { background: #cd7f32; color: #fff; }

/* ─── 模型名 ─── */
.model-name {
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  color: var(--fg-primary);
}

/* ─── 列标题内容 ─── */
.bench-name {
  display: block;
  font-weight: var(--weight-semibold);
  color: var(--fg-primary);
}
.bench-meta {
  display: block;
  color: var(--fg-tertiary);
  font-size: 10px;
  margin-top: 2px;
}
.bench-dir {
  display: block;
  font-size: 10px;
  margin-top: 2px;
}
.bench-dir[data-dir='lower_worse'] { color: var(--color-success-fg); }
.bench-dir[data-dir='higher_worse'] { color: var(--color-info-fg); }

/* ─── 最佳分高亮 ─── */
.cell--best {
  background: var(--color-success-bg);
  color: var(--color-success-fg) !important;
  font-weight: var(--weight-bold);
  border-radius: 4px;
}

/* ─── 均分列 ─── */
.avg-val {
  font-weight: var(--weight-semibold);
  color: var(--violet-600);
}
[data-theme="dark"] .avg-val,
html.dark .avg-val { color: var(--violet-300); }

.null-val { color: var(--fg-tertiary); }
</style>
