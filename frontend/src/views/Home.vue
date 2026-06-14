<template>
  <div class="home">
    <!-- 暗色 hero — marketing tier -->
    <section class="hero fc-grain">
      <div class="hero-inner">
        <div class="hero-meta">
          <span class="t-eyebrow hero-eyebrow">FANGCUN AI</span>
          <div class="hero-tags">
            <span class="hero-pill" v-if="tenantName">
              <el-icon><OfficeBuilding /></el-icon>
              <span>{{ tenantName }}</span>
            </span>
            <span class="hero-pill hero-pill--ghost" v-if="authStore.isSuperuser">
              超级管理员
            </span>
          </div>
        </div>

        <h1 class="hero-title fc-display-serif">
          {{ greeting }}，{{ authStore.user?.username }}。<br>
          继续你的<em class="fc-italic-word">分析</em>。
        </h1>
        <p class="hero-lede">
          异步任务驱动的全栈骨架。提交一个 URL 或一份 CSV，让 Worker 在后台为你完成。
        </p>

        <div class="hero-actions">
          <el-button type="primary" size="large" @click="$router.push(webpageAnalysisRoute)">
            <el-icon><Plus /></el-icon>&nbsp;新建分析任务
          </el-button>
          <el-button size="large" plain @click="$router.push(csvQualityRoute)">
            <el-icon><Grid /></el-icon>&nbsp;检查 CSV 数据
          </el-button>
        </div>

        <span class="hero-divider" aria-hidden="true"></span>
      </div>
    </section>

    <!-- 指标区 — metric callout -->
    <section class="metric-grid">
      <article class="metric-card">
        <span class="t-eyebrow">总任务</span>
        <span class="t-mono metric-card__value">{{ stats.total }}</span>
        <span class="t-caption">当前租户全部任务</span>
      </article>
      <article class="metric-card metric-card--accent">
        <span class="t-eyebrow">已完成</span>
        <span class="t-mono metric-card__value">{{ stats.success }}</span>
        <span class="t-caption">{{ percent('success') }}% 通过率</span>
      </article>
      <article class="metric-card">
        <span class="t-eyebrow">进行中</span>
        <span class="t-mono metric-card__value">{{ stats.running }}</span>
        <span class="t-caption">排队 / 处理中</span>
      </article>
      <article class="metric-card">
        <span class="t-eyebrow">失败</span>
        <span class="t-mono metric-card__value">{{ stats.failed }}</span>
        <span class="t-caption">{{ percent('failed') }}% 占比</span>
      </article>
    </section>

    <!-- 内容区 -->
    <section class="content-grid">
      <article class="content-card">
        <header class="content-card__header">
          <span class="t-eyebrow">状态分布</span>
          <h2 class="content-card__title">任务执行结果</h2>
        </header>
        <div v-if="stats.total === 0" class="content-empty">
          <span class="t-eyebrow">暂无数据</span>
          <p class="t-body-sm">提交第一个任务后这里会显示分布。</p>
        </div>
        <div v-else class="status-bars">
          <div v-for="item in statusBars" :key="item.key" class="status-bar">
            <div class="status-bar__head">
              <span class="t-body-sm">{{ item.label }}</span>
              <span class="t-mono">{{ item.value }} · {{ item.percent }}%</span>
            </div>
            <div class="status-bar__track">
              <div
                class="status-bar__fill"
                :style="{ width: item.percent + '%', background: item.color }"
              ></div>
            </div>
          </div>
        </div>
      </article>

      <article class="content-card">
        <header class="content-card__header content-card__header--row">
          <div>
            <span class="t-eyebrow">最近</span>
            <h2 class="content-card__title">最新任务</h2>
          </div>
          <el-link type="primary" :underline="false" @click="$router.push(webpageAnalysisRoute)">
            全部 →
          </el-link>
        </header>
        <div v-if="recentTasks.length === 0" class="content-empty">
          <span class="t-eyebrow">暂无记录</span>
          <p class="t-body-sm">这里会显示当前租户最近 6 条任务。</p>
        </div>
        <ul v-else class="recent-list">
          <li v-for="task in recentTasks" :key="task.id" class="recent-item">
            <span class="status-pill" :data-tone="statusTone(task.status)">
              {{ statusLabel(task.status) }}
            </span>
            <div class="recent-content">
              <div class="recent-title">{{ recentTaskTitle(task) }}</div>
              <div class="t-caption">{{ formatTime(task.created_at) }}</div>
            </div>
          </li>
        </ul>
      </article>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import { listTasks } from '../api/task'
import {
  CSV_QUALITY_TASK_TYPE,
  TASK_TYPE_LABELS,
  TASK_TYPE_ROUTES,
  WEBPAGE_ANALYSIS_TASK_TYPE,
} from '../constants/taskTypes'

const authStore = useAuthStore()
const stats = ref({ total: 0, success: 0, running: 0, failed: 0 })
const recentTasks = ref([])
const webpageAnalysisRoute = TASK_TYPE_ROUTES[WEBPAGE_ANALYSIS_TASK_TYPE]
const csvQualityRoute = TASK_TYPE_ROUTES[CSV_QUALITY_TASK_TYPE]

const tenantName = computed(() => authStore.currentTenant?.name || '')

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '夜深了'
  if (h < 11) return '早上好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

const statusBars = computed(() => {
  const t = stats.value.total || 1
  return [
    { key: 'success', label: '已完成', value: stats.value.success, percent: Math.round((stats.value.success / t) * 100), color: 'var(--sev-safe)' },
    { key: 'running', label: '进行中', value: stats.value.running, percent: Math.round((stats.value.running / t) * 100), color: 'var(--violet-500)' },
    { key: 'failed',  label: '失败',   value: stats.value.failed,  percent: Math.round((stats.value.failed  / t) * 100), color: 'var(--sev-critical)' },
  ]
})

function percent(key) {
  if (!stats.value.total) return 0
  return Math.round((stats.value[key] / stats.value.total) * 100)
}

function statusLabel(s) {
  const map = { pending: '排队中', running: '处理中', success: '已完成', failed: '失败' }
  return map[s] || s
}
function statusTone(s) {
  const map = { pending: 'neutral', running: 'progress', success: 'success', failed: 'danger' }
  return map[s] || 'neutral'
}
function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const diff = (now - d) / 1000
  if (diff < 60) return '刚刚'
  if (diff < 3600) return Math.floor(diff / 60) + ' 分钟前'
  if (diff < 86400) return Math.floor(diff / 3600) + ' 小时前'
  if (diff < 604800) return Math.floor(diff / 86400) + ' 天前'
  return d.toLocaleDateString('zh-CN')
}
function recentTaskTitle(task) {
  return TASK_TYPE_LABELS[task.task_type] || task.task_type_name || task.task_type
}

onMounted(async () => {
  try {
    const PER_PAGE = 100
    const MAX_PAGES = 5
    let allItems = []
    let total = 0
    for (let page = 1; page <= MAX_PAGES; page++) {
      const { data } = await listTasks(page, PER_PAGE)
      total = data.data.total
      allItems = allItems.concat(data.data.items)
      if (allItems.length >= total || data.data.items.length < PER_PAGE) break
    }
    stats.value.total = total
    stats.value.success = allItems.filter(i => i.status === 'success').length
    stats.value.running = allItems.filter(i => i.status === 'running' || i.status === 'pending').length
    stats.value.failed = allItems.filter(i => i.status === 'failed').length
    recentTasks.value = allItems.slice(0, 6)
  } catch (err) {
    // eslint-disable-next-line no-console
    console.warn('Home stats fetch failed:', err?.response?.data?.message || err)
  }
})
</script>

<style scoped>
.home {
  display: flex;
  flex-direction: column;
  gap: var(--space-9);
  margin: calc(var(--space-9) * -1) calc(var(--space-9) * -1) 0;
}

/* ─── Hero (dark, marketing) ─── */
.hero {
  position: relative;
  background: var(--ink-950);
  color: #f5f0ff;
  padding: var(--space-13) var(--space-12) var(--space-12);
  border-radius: 0;
  overflow: hidden;
}
.hero::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 18% 24%, rgba(143, 114, 208, 0.32) 0%, transparent 50%),
    radial-gradient(circle at 82% 78%, rgba(64, 44, 128, 0.45) 0%, transparent 60%);
  z-index: 0;
}
.hero-inner {
  position: relative;
  z-index: 2;
  max-width: 880px;
  display: flex;
  flex-direction: column;
  gap: var(--space-7);
}
.hero-meta {
  display: flex;
  align-items: center;
  gap: var(--space-7);
  flex-wrap: wrap;
}
.hero-eyebrow {
  color: rgba(245, 240, 255, 0.55);
  letter-spacing: 0.22em;
}
.hero-tags { display: flex; gap: var(--space-3); flex-wrap: wrap; }
.hero-pill {
  display: inline-flex;
  align-items: center;
  gap: var(--space-3);
  padding: 4px var(--space-5);
  border-radius: var(--radius-full);
  background: rgba(245, 240, 255, 0.08);
  color: rgba(245, 240, 255, 0.85);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
}
.hero-pill--ghost {
  background: rgba(201, 179, 126, 0.16);
  color: #c9b37e;
  border: 1px solid rgba(201, 179, 126, 0.4);
}
.hero-title {
  font-size: clamp(36px, 4.4vw, 56px);
  line-height: 1.08;
  margin: 0;
  color: #f5f0ff;
  letter-spacing: -0.01em;
}
.hero-title em {
  color: #c9b37e;
  font-style: italic;
  font-weight: 400;
}
.hero-lede {
  font-size: var(--text-lg);
  line-height: var(--leading-relaxed);
  color: rgba(245, 240, 255, 0.72);
  margin: 0;
  max-width: 56ch;
}
.hero-actions {
  display: flex;
  gap: var(--space-5);
  flex-wrap: wrap;
  margin-top: var(--space-3);
}
.hero-actions .el-button.is-plain {
  background: transparent;
  border: 1px solid rgba(245, 240, 255, 0.24);
  color: rgba(245, 240, 255, 0.92);
}
.hero-actions .el-button.is-plain:hover {
  background: rgba(245, 240, 255, 0.08);
  border-color: rgba(245, 240, 255, 0.4);
  color: #f5f0ff;
}
.hero-divider {
  width: 56px;
  height: 1px;
  background: #c9b37e;
  margin-top: var(--space-3);
}

/* ─── 指标网格 ─── */
.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--space-6);
  padding: 0 var(--space-9);
}
.metric-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: var(--space-8);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  box-shadow: var(--shadow-xs);
  transition: box-shadow var(--dur-base) var(--ease-out),
              border-color var(--dur-base) var(--ease-out);
}
.metric-card:hover {
  box-shadow: var(--shadow-sm);
  border-color: var(--border-default);
}
.metric-card--accent {
  border-color: var(--violet-200);
  background: linear-gradient(180deg, var(--violet-50) 0%, var(--bg-surface) 100%);
}
[data-theme="dark"] .metric-card--accent,
html.dark .metric-card--accent {
  border-color: rgba(143, 114, 208, 0.32);
  background: linear-gradient(180deg, rgba(109, 79, 186, 0.12) 0%, var(--bg-surface) 100%);
}
.metric-card__value {
  font-size: clamp(32px, 3.2vw, 44px);
  font-weight: var(--weight-semibold);
  color: var(--fg-primary);
  line-height: 1;
}

/* ─── 内容区 ─── */
.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.2fr);
  gap: var(--space-7);
  padding: 0 var(--space-9) var(--space-11);
}
.content-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: var(--space-8);
  display: flex;
  flex-direction: column;
  gap: var(--space-7);
  box-shadow: var(--shadow-xs);
}
.content-card__header {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.content-card__header--row {
  flex-direction: row;
  align-items: flex-end;
  justify-content: space-between;
}
.content-card__title {
  margin: 0;
  font-size: var(--text-2xl);
  font-weight: var(--weight-bold);
  color: var(--fg-primary);
  letter-spacing: -0.01em;
}
.content-empty {
  padding: var(--space-9) 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  color: var(--fg-secondary);
}

/* ─── 状态条形图 ─── */
.status-bars { display: flex; flex-direction: column; gap: var(--space-6); }
.status-bar { display: flex; flex-direction: column; gap: var(--space-3); }
.status-bar__head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  color: var(--fg-secondary);
}
.status-bar__track {
  height: 6px;
  background: var(--bg-surface-sunken);
  border-radius: var(--radius-full);
  overflow: hidden;
}
.status-bar__fill {
  height: 100%;
  border-radius: var(--radius-full);
  transition: width var(--dur-slow) var(--ease-out);
}

/* ─── 最近任务 ─── */
.recent-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
}
.recent-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-5);
  padding: var(--space-5) 0;
  border-bottom: 1px solid var(--border-subtle);
}
.recent-item:last-child { border-bottom: none; }
.recent-content { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.recent-title {
  font-size: var(--text-sm);
  color: var(--fg-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-weight: var(--weight-medium);
}

/* ─── 状态徽章 — 复用 TaskManagement 的 tone 系统 ─── */
.status-pill {
  display: inline-flex;
  align-items: center;
  padding: 2px var(--space-5);
  border-radius: var(--radius-full);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  background: var(--badge-bg-neutral);
  color: var(--badge-fg-neutral);
  border: 1px solid transparent;
  flex-shrink: 0;
  margin-top: 2px;
}
.status-pill[data-tone='success'] {
  background: var(--color-success-bg);
  color: var(--color-success-fg);
  border-color: var(--color-success-border);
}
.status-pill[data-tone='warning'] {
  background: var(--color-warning-bg);
  color: var(--color-warning-fg);
  border-color: var(--color-warning-border);
}
.status-pill[data-tone='danger'] {
  background: var(--color-danger-bg);
  color: var(--color-danger-fg);
  border-color: var(--color-danger-border);
}
.status-pill[data-tone='progress'] {
  background: var(--color-info-bg);
  color: var(--color-info-fg);
  border-color: var(--color-info-border);
}

@media (max-width: 900px) {
  .content-grid { grid-template-columns: 1fr; }
  .hero { padding: var(--space-11) var(--space-9); }
}
</style>
