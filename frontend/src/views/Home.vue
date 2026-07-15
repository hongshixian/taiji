<template>
  <div class="-mx-8 -mt-8 flex flex-col gap-9">
    <!-- 暗色 hero — marketing tier -->
    <section class="relative overflow-hidden bg-[#0a0a14] px-8 py-12 text-fg-inverse sm:px-12 sm:py-16">
      <div
        class="pointer-events-none absolute inset-0 z-0"
        style="background: radial-gradient(circle at 18% 24%, rgba(143,114,208,0.32) 0%, transparent 50%), radial-gradient(circle at 82% 78%, rgba(64,44,128,0.45) 0%, transparent 60%)"
      />
      <div class="relative z-10 flex max-w-[880px] flex-col gap-7">
        <div class="flex flex-wrap items-center gap-7">
          <span class="text-2xs font-bold uppercase tracking-[0.22em] text-white/55">FANGCUN AI</span>
          <div class="flex flex-wrap gap-2">
            <span
              v-if="tenantName"
              class="inline-flex items-center gap-2 rounded-full bg-white/10 px-4 py-1 text-xs font-semibold text-white/85"
            >
              <Building2 class="size-3.5" />
              <span>{{ tenantName }}</span>
            </span>
            <span
              v-if="authStore.isSuperuser"
              class="inline-flex items-center rounded-full border border-[#c9b37e]/40 bg-[#c9b37e]/15 px-4 py-1 text-xs font-semibold text-[#c9b37e]"
            >
              超级管理员
            </span>
          </div>
        </div>

        <h1 class="m-0 text-4xl font-black leading-[1.08] tracking-tight text-[#f5f0ff] sm:text-5xl">
          {{ greeting }}，{{ authStore.user?.username }}。<br />
          继续你的<em class="font-normal italic text-[#c9b37e]">测评</em>。
        </h1>
        <p class="m-0 max-w-[56ch] text-lg leading-relaxed text-white/70">
          提交一个测评任务，让 Worker 在后台为你完成。
        </p>

        <div class="mt-3 flex flex-wrap gap-5">
          <UiButton size="lg" @click="router.push('/tasks/benchmark')">
            <template #icon><Plus class="size-4" /></template>
            新建测评任务
          </UiButton>
          <UiButton
            variant="secondary"
            size="lg"
            class="border-white/25 bg-transparent text-white/90 hover:border-white/40 hover:bg-white/10 hover:text-white"
            @click="router.push('/leaderboard')"
          >
            <template #icon><BarChart3 class="size-4" /></template>
            查看测评榜单
          </UiButton>
        </div>

        <span class="mt-3 h-px w-14 bg-[#c9b37e]" />
      </div>
    </section>

    <!-- 指标区 — metric callout -->
    <section class="grid grid-cols-1 gap-6 px-8 sm:grid-cols-2 lg:grid-cols-4">
      <article class="flex flex-col gap-3 rounded-lg border border-line bg-surface p-8 shadow-xs transition-shadow hover:shadow-sm">
        <span class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">总任务</span>
        <span class="font-mono text-4xl font-semibold leading-none text-fg">{{ stats.total }}</span>
        <span class="text-xs text-fg-tertiary">当前租户全部任务</span>
      </article>
      <article class="flex flex-col gap-3 rounded-lg border border-brand/30 bg-brand-soft p-8 shadow-xs transition-shadow hover:shadow-sm">
        <span class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">已完成</span>
        <span class="font-mono text-4xl font-semibold leading-none text-fg">{{ stats.success }}</span>
        <span class="text-xs text-fg-tertiary">{{ percent('success') }}% 通过率</span>
      </article>
      <article class="flex flex-col gap-3 rounded-lg border border-line bg-surface p-8 shadow-xs transition-shadow hover:shadow-sm">
        <span class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">进行中</span>
        <span class="font-mono text-4xl font-semibold leading-none text-fg">{{ stats.running }}</span>
        <span class="text-xs text-fg-tertiary">排队 / 处理中</span>
      </article>
      <article class="flex flex-col gap-3 rounded-lg border border-line bg-surface p-8 shadow-xs transition-shadow hover:shadow-sm">
        <span class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">失败</span>
        <span class="font-mono text-4xl font-semibold leading-none text-fg">{{ stats.failed }}</span>
        <span class="text-xs text-fg-tertiary">{{ percent('failed') }}% 占比</span>
      </article>
    </section>

    <!-- 内容区 -->
    <section class="grid grid-cols-1 gap-7 px-8 pb-11 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]">
      <!-- 状态分布 -->
      <article class="flex flex-col gap-7 rounded-lg border border-line bg-surface p-8 shadow-xs">
        <header class="flex flex-col gap-1">
          <span class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">状态分布</span>
          <h2 class="m-0 text-2xl font-bold tracking-tight text-fg">任务执行结果</h2>
        </header>
        <div v-if="stats.total === 0" class="flex flex-col items-center gap-3 py-9 text-fg-secondary">
          <span class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">暂无数据</span>
          <p class="m-0 text-sm">提交第一个任务后这里会显示分布。</p>
        </div>
        <div v-else class="flex flex-col gap-6">
          <div v-for="item in statusBars" :key="item.key" class="flex flex-col gap-3">
            <div class="flex items-baseline justify-between text-fg-secondary">
              <span class="text-sm">{{ item.label }}</span>
              <span class="font-mono text-sm">{{ item.value }} · {{ item.percent }}%</span>
            </div>
            <div class="h-1.5 overflow-hidden rounded-full bg-surface-sunken">
              <div
                class="h-full rounded-full transition-[width] duration-500"
                :class="item.barClass"
                :style="{ width: item.percent + '%' }"
              />
            </div>
          </div>
        </div>
      </article>

      <!-- 最近任务 -->
      <article class="flex flex-col gap-7 rounded-lg border border-line bg-surface p-8 shadow-xs">
        <header class="flex items-end justify-between gap-4">
          <div class="flex flex-col gap-1">
            <span class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">最近</span>
            <h2 class="m-0 text-2xl font-bold tracking-tight text-fg">最新任务</h2>
          </div>
          <router-link to="/tasks/benchmark" class="text-sm font-semibold text-brand hover:underline">
            全部 →
          </router-link>
        </header>
        <div v-if="recentTasks.length === 0" class="flex flex-col items-center gap-3 py-9 text-fg-secondary">
          <span class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">暂无记录</span>
          <p class="m-0 text-sm">这里会显示当前租户最近 6 条任务。</p>
        </div>
        <ul v-else class="m-0 flex list-none flex-col p-0">
          <li
            v-for="task in recentTasks"
            :key="task.id"
            class="flex items-start gap-5 border-b border-line py-5 last:border-b-0"
          >
            <UiBadge :tone="statusTone(task.status)" class="mt-0.5 shrink-0">
              {{ statusLabel(task.status) }}
            </UiBadge>
            <div class="flex min-w-0 flex-1 flex-col gap-0.5">
              <div class="truncate text-sm font-medium text-fg">{{ recentTaskTitle(task) }}</div>
              <div class="text-xs text-fg-tertiary">{{ formatTime(task.created_at) }}</div>
            </div>
          </li>
        </ul>
      </article>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Building2, Plus, BarChart3 } from 'lucide-vue-next'
import UiButton from '@/components/ui/Button.vue'
import UiBadge from '@/components/ui/Badge.vue'
import { useAuthStore } from '@/stores/auth'
import { listTasks } from '@/api/task'
import { TASK_TYPE_LABELS } from '@/constants/taskTypes'

type BadgeTone = 'neutral' | 'brand' | 'success' | 'warning' | 'danger' | 'info'

interface TaskItem {
  id: number | string
  status: string
  task_type: string
  task_type_name?: string
  created_at?: string
}

interface Stats {
  total: number
  success: number
  running: number
  failed: number
}

const router = useRouter()
const authStore = useAuthStore()
const stats = ref<Stats>({ total: 0, success: 0, running: 0, failed: 0 })
const recentTasks = ref<TaskItem[]>([])

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
    { key: 'success', label: '已完成', value: stats.value.success, percent: Math.round((stats.value.success / t) * 100), barClass: 'bg-success' },
    { key: 'running', label: '进行中', value: stats.value.running, percent: Math.round((stats.value.running / t) * 100), barClass: 'bg-brand' },
    { key: 'failed', label: '失败', value: stats.value.failed, percent: Math.round((stats.value.failed / t) * 100), barClass: 'bg-danger' },
  ]
})

function percent(key: 'success' | 'failed'): number {
  if (!stats.value.total) return 0
  return Math.round((stats.value[key] / stats.value.total) * 100)
}

function statusLabel(s: string): string {
  const map: Record<string, string> = { pending: '排队中', running: '处理中', success: '已完成', failed: '失败' }
  return map[s] || s
}
function statusTone(s: string): BadgeTone {
  const map: Record<string, BadgeTone> = { pending: 'neutral', running: 'info', success: 'success', failed: 'danger' }
  return map[s] || 'neutral'
}
function formatTime(iso?: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const diff = (now.getTime() - d.getTime()) / 1000
  if (diff < 60) return '刚刚'
  if (diff < 3600) return Math.floor(diff / 60) + ' 分钟前'
  if (diff < 86400) return Math.floor(diff / 3600) + ' 小时前'
  if (diff < 604800) return Math.floor(diff / 86400) + ' 天前'
  return d.toLocaleDateString('zh-CN')
}
function recentTaskTitle(task: TaskItem): string {
  return (TASK_TYPE_LABELS as Record<string, string>)[task.task_type] || task.task_type_name || task.task_type
}

onMounted(async () => {
  try {
    const PER_PAGE = 100
    const MAX_PAGES = 5
    let allItems: TaskItem[] = []
    let total = 0
    for (let page = 1; page <= MAX_PAGES; page++) {
      const { data } = await listTasks(page, PER_PAGE)
      total = data.data.total
      allItems = allItems.concat(data.data.items)
      if (allItems.length >= total || data.data.items.length < PER_PAGE) break
    }
    stats.value.total = total
    stats.value.success = allItems.filter((i) => i.status === 'success').length
    stats.value.running = allItems.filter((i) => i.status === 'running' || i.status === 'pending').length
    stats.value.failed = allItems.filter((i) => i.status === 'failed').length
    recentTasks.value = allItems.slice(0, 6)
  } catch (err: unknown) {
    const e = err as { response?: { data?: { message?: string } } }
    // eslint-disable-next-line no-console
    console.warn('Home stats fetch failed:', e.response?.data?.message || err)
  }
})
</script>
