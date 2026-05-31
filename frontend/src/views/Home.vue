<template>
  <div class="home">
    <!-- Hero 欢迎区 -->
    <div class="hero">
      <div class="hero-text">
        <div class="hero-greeting">
          {{ greeting }}，{{ authStore.user?.username }} 👋
          <el-tag v-if="tenantName" size="small" effect="dark" class="hero-tenant-tag">
            <el-icon><OfficeBuilding /></el-icon>
            <span>{{ tenantName }}</span>
          </el-tag>
          <el-tag v-if="authStore.isSuperuser" size="small" type="danger" effect="dark" class="hero-tenant-tag">
            超级管理员
          </el-tag>
        </div>
        <h1 class="hero-title">欢迎使用<span class="taiji-gradient-text">太极</span>平台</h1>
        <p class="hero-desc">异步任务驱动 · 一站式网页内容分析</p>
        <div class="hero-actions">
          <el-button type="primary" size="large" @click="$router.push('/tasks')">
            <el-icon><Plus /></el-icon>&nbsp;新建分析任务
          </el-button>
          <el-button size="large" plain @click="$router.push('/tasks')">
            <el-icon><Document /></el-icon>&nbsp;查看任务列表
          </el-button>
        </div>
      </div>
      <div class="hero-decoration">
        <img src="../assets/taiji-logo.svg" alt="" class="hero-logo" />
      </div>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card is-hover-shadow">
          <div class="stat-icon-wrap stat-total">
            <el-icon><DataAnalysis /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.total }}</div>
            <div class="stat-label">总任务数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card is-hover-shadow">
          <div class="stat-icon-wrap stat-success">
            <el-icon><CircleCheck /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.success }}</div>
            <div class="stat-label">已完成</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card is-hover-shadow">
          <div class="stat-icon-wrap stat-running">
            <el-icon><Loading /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.running }}</div>
            <div class="stat-label">进行中</div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="stat-card is-hover-shadow">
          <div class="stat-icon-wrap stat-failed">
            <el-icon><CircleClose /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.failed }}</div>
            <div class="stat-label">失败</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="content-row">
      <!-- 任务状态分布（纯 CSS 条形图） -->
      <el-col :xs="24" :md="10">
        <el-card shadow="never" class="content-card">
          <template #header>
            <div class="card-title">
              <el-icon><PieChart /></el-icon>&nbsp;任务状态分布
            </div>
          </template>
          <div v-if="stats.total === 0" class="empty-mini">
            <el-empty description="暂无数据" :image-size="80" />
          </div>
          <div v-else class="status-bars">
            <div v-for="item in statusBars" :key="item.key" class="status-bar-item">
              <div class="status-bar-label">
                <span>{{ item.label }}</span>
                <span class="status-bar-count">{{ item.value }} ({{ item.percent }}%)</span>
              </div>
              <div class="status-bar-track">
                <div class="status-bar-fill" :style="{ width: item.percent + '%', background: item.color }"></div>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 最近任务 -->
      <el-col :xs="24" :md="14">
        <el-card shadow="never" class="content-card">
          <template #header>
            <div class="card-title">
              <span><el-icon><Clock /></el-icon>&nbsp;最近任务</span>
              <el-link type="primary" :underline="false" @click="$router.push('/tasks')">查看全部 →</el-link>
            </div>
          </template>
          <div v-if="recentTasks.length === 0" class="empty-mini">
            <el-empty description="暂无任务记录" :image-size="80" />
          </div>
          <ul v-else class="recent-list">
            <li v-for="task in recentTasks" :key="task.id" class="recent-item">
              <el-tag :type="statusTagType(task.status)" size="small" class="recent-tag">
                {{ statusLabel(task.status) }}
              </el-tag>
              <div class="recent-content">
                <div class="recent-title">{{ task.title || task.url }}</div>
                <div class="recent-meta">{{ formatTime(task.created_at) }}</div>
              </div>
            </li>
          </ul>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import { listAnalyses } from '../api/analyze'

const authStore = useAuthStore()
const stats = ref({ total: 0, success: 0, running: 0, failed: 0 })
const recentTasks = ref([])

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
    { key: 'success', label: '已完成', value: stats.value.success, percent: Math.round((stats.value.success / t) * 100), color: 'var(--taiji-jade)' },
    { key: 'running', label: '进行中', value: stats.value.running, percent: Math.round((stats.value.running / t) * 100), color: 'var(--taiji-gold)' },
    { key: 'failed', label: '失败', value: stats.value.failed, percent: Math.round((stats.value.failed / t) * 100), color: 'var(--taiji-accent)' },
  ]
})

function statusLabel(s) {
  const map = { pending: '排队中', running: '分析中', success: '已完成', failed: '失败' }
  return map[s] || s
}
function statusTagType(s) {
  const map = { pending: 'info', running: 'warning', success: 'success', failed: 'danger' }
  return map[s] || 'info'
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

onMounted(async () => {
  try {
    // 后端 per_page 上限 100；分页累加获取（最多 5 页 = 500 条已足够首页统计）
    const PER_PAGE = 100
    const MAX_PAGES = 5
    let allItems = []
    let total = 0
    for (let page = 1; page <= MAX_PAGES; page++) {
      const { data } = await listAnalyses(page, PER_PAGE)
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
.home { max-width: 1280px; margin: 0 auto; }

/* ─── Hero ───────────────────────────── */
.hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 36px 40px;
  background: var(--taiji-gradient-hero);
  border-radius: var(--taiji-radius-lg);
  color: #fff;
  margin-bottom: 24px;
  overflow: hidden;
  position: relative;
  box-shadow: var(--taiji-shadow-md);
}
.hero-greeting {
  font-size: 14px;
  opacity: 0.9;
  letter-spacing: 1px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.hero-tenant-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.hero-title {
  font-size: 32px;
  font-weight: 600;
  margin: 8px 0 12px;
  letter-spacing: 2px;
}
.hero-title .taiji-gradient-text { padding: 0 6px; }
.hero-desc { font-size: 14px; opacity: 0.75; margin: 0 0 24px; letter-spacing: 1px; }
.hero-actions { display: flex; gap: 12px; flex-wrap: wrap; }
.hero-actions .el-button { border: none; }
.hero-decoration {
  position: relative;
  width: 180px;
  height: 180px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.hero-logo {
  width: 160px;
  height: 160px;
  opacity: 0.85;
  filter: drop-shadow(0 4px 24px rgba(0, 0, 0, 0.4));
  animation: spin 30s linear infinite;
}
@keyframes spin { to { transform: rotate(-360deg); } }

/* ─── 统计卡片 ───────────────────────── */
.stats-row { margin-bottom: 24px; }
.stat-card { cursor: default; }
.stat-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
}
.stat-icon-wrap {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  color: #fff;
  flex-shrink: 0;
}
.stat-total   { background: linear-gradient(135deg, #2c3e50, #4a6278); }
.stat-success { background: linear-gradient(135deg, #16a085, #1abc9c); }
.stat-running { background: linear-gradient(135deg, #d4a017, #f39c12); }
.stat-failed  { background: linear-gradient(135deg, #c0392b, #e74c3c); }
.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  line-height: 1.2;
}
.stat-label {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  margin-top: 2px;
}

/* ─── 内容卡片 ───────────────────────── */
.content-row { margin-top: 0; }
.content-card { border: 1px solid var(--el-border-color-lighter); }
.card-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 15px;
  font-weight: 500;
  color: var(--el-text-color-primary);
}
.empty-mini { padding: 20px 0; }

/* ─── 状态条形图 ─────────────────────── */
.status-bars { display: flex; flex-direction: column; gap: 18px; padding: 8px 0; }
.status-bar-label {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: var(--el-text-color-regular);
  margin-bottom: 6px;
}
.status-bar-count { color: var(--el-text-color-secondary); font-variant-numeric: tabular-nums; }
.status-bar-track {
  width: 100%;
  height: 8px;
  background: var(--el-fill-color);
  border-radius: 4px;
  overflow: hidden;
}
.status-bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.6s ease;
}

/* ─── 最近任务列表 ───────────────────── */
.recent-list { list-style: none; padding: 0; margin: 0; }
.recent-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 4px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.recent-item:last-child { border-bottom: none; }
.recent-tag { flex-shrink: 0; margin-top: 2px; }
.recent-content { flex: 1; min-width: 0; }
.recent-title {
  font-size: 13px;
  color: var(--el-text-color-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.recent-meta {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 2px;
}

@media (max-width: 768px) {
  .hero { flex-direction: column; padding: 24px; text-align: center; }
  .hero-decoration { margin-top: 16px; width: 100px; height: 100px; }
  .hero-logo { width: 100px; height: 100px; }
  .hero-title { font-size: 24px; }
}
</style>
