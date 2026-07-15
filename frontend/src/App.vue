<template>
  <div id="app">
    <div v-if="isLoggedIn" class="flex h-screen flex-col">
      <!-- 顶栏 -->
      <header class="relative z-10 flex h-16 shrink-0 items-center justify-between border-b border-line bg-surface px-6">
        <div class="flex items-center gap-5">
          <button
            type="button"
            class="flex size-9 items-center justify-center rounded-md text-fg-secondary transition-colors hover:bg-surface-sunken hover:text-fg"
            :aria-label="collapsed ? '展开侧边栏' : '收起侧边栏'"
            @click="collapsed = !collapsed"
          >
            <PanelLeft v-if="collapsed" class="size-5" />
            <PanelLeftClose v-else class="size-5" />
          </button>
          <router-link to="/" class="flex items-center gap-3" aria-label="返回主页">
            <img src="./assets/brand/logo-mark-purple.svg" alt="" class="size-9 rounded-md" />
            <span class="flex flex-col leading-tight">
              <span class="text-lg font-bold tracking-wide text-fg">{{ t('nav.brand') }}</span>
              <span class="font-mono text-[10px] uppercase tracking-[0.18em] text-fg-tertiary">{{ t('nav.brandSub') }}</span>
            </span>
          </router-link>
        </div>

        <div class="flex items-center gap-3">
          <TenantSwitcher />

          <button
            type="button"
            class="flex h-9 items-center gap-1 rounded-md px-2 text-sm font-medium text-fg-secondary transition-colors hover:bg-surface-sunken hover:text-fg"
            :title="t('nav.toggleLang')"
            @click="toggleLocale"
          >
            <Languages class="size-4" />
            <span>{{ locale === 'zh' ? 'EN' : '中' }}</span>
          </button>

          <button
            type="button"
            class="flex size-9 items-center justify-center rounded-md text-fg-secondary transition-colors hover:bg-surface-sunken hover:text-fg"
            :aria-label="isDark ? t('nav.toggleLight') : t('nav.toggleDark')"
            :title="isDark ? t('nav.toggleLight') : t('nav.toggleDark')"
            @click="toggleTheme"
          >
            <Sun v-if="isDark" class="size-5" />
            <Moon v-else class="size-5" />
          </button>

          <UiDropdown>
            <template #trigger>
              <button type="button" class="flex items-center gap-2 rounded-full border border-transparent p-1 pr-3 transition-colors hover:border-line hover:bg-surface-sunken">
                <span
                  class="flex size-8 items-center justify-center rounded-full text-sm font-semibold text-brand-fg"
                  :class="authStore.isSuperuser ? 'bg-gradient-to-br from-violet-700 to-violet-300 ring-2 ring-brand/25' : 'bg-violet-600'"
                >
                  {{ avatarInitial }}
                </span>
                <span class="hidden flex-col leading-tight sm:flex">
                  <span class="text-sm font-semibold text-fg">{{ authStore.user?.username }}</span>
                  <span class="text-xs text-fg-tertiary">{{ roleLabel }}</span>
                </span>
                <ChevronDown class="size-3 text-fg-tertiary" />
              </button>
            </template>
            <template #default="{ close }">
              <UiDropdownItem @select="close(); router.push('/settings')">
                <Settings class="size-4" /> {{ t('nav.personalSettings') }}
              </UiDropdownItem>
              <div class="my-1 border-t border-line" />
              <UiDropdownItem @select="close(); authStore.logout()">
                <LogOut class="size-4" /> {{ t('nav.logout') }}
              </UiDropdownItem>
            </template>
          </UiDropdown>
        </div>
      </header>

      <div class="flex min-h-0 flex-1">
        <!-- 侧边栏 -->
        <aside
          class="flex shrink-0 flex-col justify-between overflow-hidden border-r border-line bg-surface transition-[width] duration-300"
          :class="collapsed ? 'w-16' : 'w-56'"
        >
          <nav class="flex-1 space-y-1 p-3">
            <template v-for="item in menu" :key="item.key">
              <!-- 分组（任务管理） -->
              <div v-if="item.children">
                <button
                  type="button"
                  class="flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-fg-secondary transition-colors hover:bg-surface-sunken hover:text-fg"
                  @click="toggleGroup(item.key)"
                >
                  <component :is="item.icon" class="size-[18px] shrink-0" />
                  <template v-if="!collapsed">
                    <span class="flex-1 text-left">{{ item.label }}</span>
                    <ChevronDown :class="cn('size-4 transition-transform', openGroups.includes(item.key) && 'rotate-180')" />
                  </template>
                </button>
                <div v-if="!collapsed && openGroups.includes(item.key)" class="mt-1 space-y-1 pl-4">
                  <router-link
                    v-for="child in item.children"
                    :key="child.to"
                    :to="child.to"
                    :class="navClass(isActive(child.to))"
                  >
                    <component :is="child.icon" class="size-[18px] shrink-0" />
                    <span>{{ child.label }}</span>
                  </router-link>
                </div>
              </div>
              <!-- 普通项 -->
              <router-link v-else :to="item.to!" :class="navClass(isActive(item.to!))" :title="collapsed ? item.label : undefined">
                <component :is="item.icon" class="size-[18px] shrink-0" />
                <span v-if="!collapsed">{{ item.label }}</span>
              </router-link>
            </template>
          </nav>
          <div v-if="!collapsed" class="flex flex-col gap-1 border-t border-line px-5 py-4">
            <span class="text-2xs font-bold uppercase tracking-widest text-fg-tertiary">Fangcun AI</span>
            <span class="font-mono text-xs text-fg-tertiary">{{ t('nav.version') }}</span>
          </div>
        </aside>

        <!-- 主内容区 -->
        <main class="min-w-0 flex-1 overflow-y-auto bg-canvas p-8">
          <router-view v-slot="{ Component }">
            <transition name="fade-slide" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </main>
      </div>
    </div>

    <router-view v-else v-slot="{ Component }">
      <transition name="fade-slide" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>

    <Toaster />
    <ConfirmHost />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, type Component } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  PanelLeft, PanelLeftClose, Sun, Moon, ChevronDown, Settings, LogOut, Languages,
  Home, Trophy, ListChecks, BarChart3, ShieldAlert, Cpu, Users, KeyRound,
  ScrollText, Wrench, Building2, SlidersHorizontal,
} from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from './stores/auth'
import { usePermission } from './composables/usePermission'
import TenantSwitcher from './components/TenantSwitcher.vue'
import Toaster from './components/ui/Toaster.vue'
import ConfirmHost from './components/ui/ConfirmHost.vue'
import UiDropdown from './components/ui/Dropdown.vue'
import UiDropdownItem from './components/ui/DropdownItem.vue'
import { applyTheme, isDarkActive } from './utils/theme'
import { setLocale, type AppLocale } from './i18n'
import {
  BENCHMARK_TASK_TYPE,
  RED_TEAM_TASK_TYPE,
  TASK_TYPE_ROUTES,
} from './constants/taskTypes'
import { cn } from '@/lib/utils'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const { has } = usePermission()
const { t, locale } = useI18n()

function toggleLocale() {
  setLocale((locale.value === 'zh' ? 'en' : 'zh') as AppLocale)
}

const collapsed = ref(window.innerWidth < 900)
const isDark = ref(isDarkActive())
const openGroups = ref<string[]>(route.path.startsWith('/tasks') ? ['tasks'] : [])

interface MenuChild { to: string; label: string; icon: Component }
interface MenuItem { key: string; label: string; icon: Component; to?: string; children?: MenuChild[]; show?: boolean }

const menu = computed<MenuItem[]>(() =>
  ([
    { key: 'home', label: t('nav.home'), icon: Home, to: '/', show: true },
    { key: 'leaderboard', label: t('nav.leaderboard'), icon: Trophy, to: '/leaderboard', show: true },
    {
      key: 'tasks', label: t('nav.tasks'), icon: ListChecks, show: has('task:read'),
      children: [
        { to: TASK_TYPE_ROUTES[BENCHMARK_TASK_TYPE], label: t('nav.benchmark'), icon: BarChart3 },
        { to: TASK_TYPE_ROUTES[RED_TEAM_TASK_TYPE], label: t('nav.redteam'), icon: ShieldAlert },
      ],
    },
    { key: 'models', label: t('nav.models'), icon: Cpu, to: '/models', show: has('model:read') },
    { key: 'users', label: t('nav.users'), icon: Users, to: '/users', show: has('user:read') },
    { key: 'roles', label: t('nav.roles'), icon: KeyRound, to: '/roles', show: has('role:read') },
    { key: 'audit', label: t('nav.audit'), icon: ScrollText, to: '/audit-logs', show: has('system:audit') },
    { key: 'settings', label: t('nav.settings'), icon: Wrench, to: '/settings', show: true },
    { key: 'tenants', label: t('nav.tenants'), icon: Building2, to: '/tenants', show: authStore.isSuperuser },
    { key: 'sys', label: t('nav.systemSettings'), icon: SlidersHorizontal, to: '/system-settings', show: authStore.isSuperuser },
  ] as MenuItem[]).filter((m) => m.show !== false),
)

const isLoggedIn = computed(() => authStore.isLoggedIn)
const avatarInitial = computed(() => (authStore.user?.username || '?').charAt(0).toUpperCase())
const roleLabel = computed(() => {
  const u = authStore.user
  if (!u) return ''
  if (u.is_superuser) return t('nav.superadmin')
  return (u as { role_name?: string }).role_name || u.role || t('nav.normalUser')
})

function isActive(path: string) {
  return path === '/' ? route.path === '/' : route.path.startsWith(path)
}
function navClass(active: boolean) {
  return cn(
    'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
    active ? 'bg-brand-soft text-brand' : 'text-fg-secondary hover:bg-surface-sunken hover:text-fg',
  )
}
function toggleGroup(key: string) {
  openGroups.value = openGroups.value.includes(key)
    ? openGroups.value.filter((k) => k !== key)
    : [...openGroups.value, key]
}
function toggleTheme() {
  isDark.value = !isDark.value
  applyTheme(isDark.value)
}
function handleResize() {
  if (window.innerWidth < 900) collapsed.value = true
}
onMounted(() => window.addEventListener('resize', handleResize))
onUnmounted(() => window.removeEventListener('resize', handleResize))
</script>

<style>
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: opacity var(--dur-base) var(--ease-out), transform var(--dur-base) var(--ease-out);
}
.fade-slide-enter-from { opacity: 0; transform: translateY(8px); }
.fade-slide-leave-to { opacity: 0; transform: translateY(-8px); }
</style>
