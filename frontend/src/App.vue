<template>
  <div id="app">
    <el-container v-if="isLoggedIn" class="app-layout">
      <!-- 顶栏 -->
      <el-header class="app-header">
        <div class="header-left">
          <button
            type="button"
            class="collapse-btn fc-focus"
            :aria-label="collapsed ? '展开侧边栏' : '收起侧边栏'"
            @click="collapsed = !collapsed"
          >
            <el-icon><component :is="collapsed ? 'Expand' : 'Fold'" /></el-icon>
          </button>
          <router-link to="/" class="brand fc-focus" aria-label="返回主页">
            <img src="./assets/brand/logo-mark-purple.svg" alt="" class="brand-logo" />
            <span class="brand-stack">
              <span class="brand-mark">方寸AI测评平台</span>
              <span class="brand-sub">Fangcun AI Evaluation Platform</span>
            </span>
          </router-link>
        </div>

        <div class="header-right">
          <TenantSwitcher />

          <el-tooltip :content="isDark ? '切换为浅色' : '切换为深色'" placement="bottom">
            <button
              type="button"
              class="header-icon fc-focus"
              :aria-label="isDark ? '切换为浅色' : '切换为深色'"
              @click="toggleTheme"
            >
              <el-icon><component :is="isDark ? 'Sunny' : 'Moon'" /></el-icon>
            </button>
          </el-tooltip>

          <el-dropdown trigger="click" @command="handleCommand">
            <button type="button" class="user-trigger fc-focus">
              <el-avatar :size="32" class="user-avatar" :class="{ 'is-superuser': authStore.isSuperuser }">
                {{ avatarInitial }}
              </el-avatar>
              <span class="user-meta">
                <span class="username">{{ authStore.user?.username }}</span>
                <span class="user-role">{{ roleLabel }}</span>
              </span>
              <el-icon class="caret"><ArrowDown /></el-icon>
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="settings">
                  <el-icon><Setting /></el-icon> 个人设置
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon> 退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-container>
        <el-aside :width="collapsed ? '64px' : '224px'" class="app-aside">
          <el-menu
            :default-active="currentRoute"
            :default-openeds="defaultOpeneds"
            :collapse="collapsed"
            router
            class="side-menu"
          >
            <el-menu-item index="/">
              <el-icon><HomeFilled /></el-icon>
              <template #title>主页</template>
            </el-menu-item>
            <el-menu-item index="/leaderboard">
              <el-icon><TrophyBase /></el-icon>
              <template #title>测评榜单</template>
            </el-menu-item>
            <el-sub-menu index="/tasks" v-if="has('task:read')">
              <template #title>
                <el-icon><Tickets /></el-icon>
                <span>任务管理</span>
              </template>
              <el-menu-item :index="TASK_TYPE_ROUTES[BENCHMARK_TASK_TYPE]">
                <el-icon><DataAnalysis /></el-icon>
                <template #title>Benchmark 测评</template>
              </el-menu-item>
              <el-menu-item :index="TASK_TYPE_ROUTES[RED_TEAM_TASK_TYPE]">
                <el-icon><Warning /></el-icon>
                <template #title>自动红队测评</template>
              </el-menu-item>
            </el-sub-menu>
            <el-menu-item index="/models" v-if="has('model:read')">
              <el-icon><Cpu /></el-icon>
              <template #title>模型管理</template>
            </el-menu-item>
            <el-menu-item index="/users" v-if="has('user:read')">
              <el-icon><User /></el-icon>
              <template #title>用户管理</template>
            </el-menu-item>
            <el-menu-item index="/roles" v-if="has('role:read')">
              <el-icon><Key /></el-icon>
              <template #title>角色管理</template>
            </el-menu-item>
            <el-menu-item index="/audit-logs" v-if="has('system:audit')">
              <el-icon><Tickets /></el-icon>
              <template #title>审计日志</template>
            </el-menu-item>
            <el-menu-item index="/settings">
              <el-icon><Tools /></el-icon>
              <template #title>通用设置</template>
            </el-menu-item>
            <el-menu-item index="/tenants" v-if="authStore.isSuperuser">
              <el-icon><OfficeBuilding /></el-icon>
              <template #title>租户管理</template>
            </el-menu-item>
            <el-menu-item index="/system-settings" v-if="authStore.isSuperuser">
              <el-icon><Operation /></el-icon>
              <template #title>系统设置</template>
            </el-menu-item>
          </el-menu>
          <div v-if="!collapsed" class="aside-footer">
            <span class="t-eyebrow">Fangcun AI</span>
            <span class="aside-version">v0.1</span>
          </div>
        </el-aside>

        <el-main class="app-main">
          <router-view v-slot="{ Component }">
            <transition name="fade-slide" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </el-main>
      </el-container>
    </el-container>

    <router-view v-else v-slot="{ Component }">
      <transition name="fade-slide" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'
import { usePermission } from './composables/usePermission'
import TenantSwitcher from './components/TenantSwitcher.vue'
import { applyTheme, isDarkActive } from './utils/theme'
import {
  BENCHMARK_TASK_TYPE,
  RED_TEAM_TASK_TYPE,
  TASK_TYPE_ROUTES,
} from './constants/taskTypes'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const { has } = usePermission()

const collapsed = ref(window.innerWidth < 900)
const isDark = ref(isDarkActive())

const isLoggedIn = computed(() => authStore.isLoggedIn)
const currentRoute = computed(() => route.path)
const defaultOpeneds = computed(() => (
  route.path.startsWith('/tasks') ? ['/tasks'] : []
))
const avatarInitial = computed(() => {
  const name = authStore.user?.username || '?'
  return name.charAt(0).toUpperCase()
})

const roleLabel = computed(() => {
  const u = authStore.user
  if (!u) return ''
  if (u.is_superuser) return '超级管理员'
  return u.role_name || u.role || '普通用户'
})

function toggleTheme() {
  isDark.value = !isDark.value
  applyTheme(isDark.value)
}

function handleCommand(cmd) {
  if (cmd === 'logout') {
    authStore.logout()
  } else if (cmd === 'settings') {
    router.push('/settings')
  }
}

function handleResize() {
  if (window.innerWidth < 900) {
    collapsed.value = true
  }
}
onMounted(() => window.addEventListener('resize', handleResize))
onUnmounted(() => window.removeEventListener('resize', handleResize))
</script>

<style>
.app-layout { height: 100vh; }

/* ─── 顶栏 ───────────────────────────────── */
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-subtle);
  padding: 0 var(--space-8);
  height: 64px;
  z-index: 10;
  position: relative;
}
.header-left { display: flex; align-items: center; gap: var(--space-7); }

.collapse-btn {
  width: 36px; height: 36px;
  display: inline-flex; align-items: center; justify-content: center;
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  color: var(--fg-secondary);
  font-size: 18px;
  transition: background var(--dur-base) var(--ease-out),
              color var(--dur-base) var(--ease-out);
}
.collapse-btn:hover {
  background: var(--state-hover);
  color: var(--fg-primary);
}

.brand {
  display: flex;
  align-items: center;
  gap: var(--space-5);
  text-decoration: none;
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
}
.brand-logo { width: 72px; height: 72px; }
.brand-stack { display: flex; flex-direction: column; line-height: 1.1; }
.brand-mark {
  font-size: var(--text-lg);
  font-weight: var(--weight-bold);
  letter-spacing: 0.04em;
  color: var(--fg-primary);
}
.brand-sub {
  font-family: var(--font-mono);
  font-size: var(--text-3xs);
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--fg-tertiary);
  margin-top: 2px;
}

.header-right { display: flex; align-items: center; gap: var(--space-5); }

.header-icon {
  width: 36px; height: 36px;
  display: inline-flex; align-items: center; justify-content: center;
  background: transparent;
  border: none;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: 18px;
  color: var(--fg-secondary);
  transition: background var(--dur-base) var(--ease-out),
              color var(--dur-base) var(--ease-out);
}
.header-icon:hover {
  background: var(--state-hover);
  color: var(--fg-primary);
}

.user-trigger {
  display: flex;
  align-items: center;
  gap: var(--space-5);
  cursor: pointer;
  padding: var(--space-2) var(--space-5) var(--space-2) var(--space-2);
  border: 1px solid transparent;
  border-radius: var(--radius-full);
  background: transparent;
  transition: background var(--dur-base) var(--ease-out),
              border-color var(--dur-base) var(--ease-out);
}
.user-trigger:hover {
  background: var(--state-hover);
  border-color: var(--border-subtle);
}
.user-avatar {
  background: var(--violet-600);
  color: var(--fg-on-brand);
  font-weight: var(--weight-semibold);
}
.user-avatar.is-superuser {
  background: var(--brand-gradient);
  box-shadow: 0 0 0 2px rgba(109, 79, 186, 0.25);
}
.user-meta { display: flex; flex-direction: column; line-height: 1.2; }
.username {
  color: var(--fg-primary);
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
}
.user-role {
  color: var(--fg-tertiary);
  font-size: var(--text-xs);
  margin-top: 2px;
}
.caret { font-size: 12px; color: var(--fg-tertiary); }

/* ─── 侧边栏 ─────────────────────────────── */
.app-aside {
  background: var(--bg-surface);
  border-right: 1px solid var(--border-subtle);
  transition: width var(--dur-slow) var(--ease-out);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
.side-menu {
  border-right: none !important;
  flex: 1;
  background: transparent;
  padding: var(--space-5) var(--space-4);
}
.side-menu .el-menu-item,
.side-menu .el-sub-menu__title {
  height: 40px;
  line-height: 40px;
  margin: var(--space-2) 0;
  border-radius: var(--radius-md);
  color: var(--fg-secondary);
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
}
.side-menu .el-menu-item:hover,
.side-menu .el-sub-menu__title:hover {
  background: var(--state-hover) !important;
  color: var(--fg-primary) !important;
}
.side-menu .el-sub-menu .el-menu-item {
  margin-left: var(--space-5);
  min-width: 0;
}
.side-menu .el-menu-item.is-active {
  background: var(--state-selected) !important;
  color: var(--violet-600);
  font-weight: var(--weight-semibold);
  position: relative;
}
[data-theme="dark"] .side-menu .el-menu-item.is-active,
html.dark .side-menu .el-menu-item.is-active {
  color: var(--violet-300);
}
.side-menu .el-menu-item.is-active::before {
  content: '';
  position: absolute;
  left: -4px;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 60%;
  background: var(--violet-600);
  border-radius: 0 var(--radius-xs) var(--radius-xs) 0;
}
[data-theme="dark"] .side-menu .el-menu-item.is-active::before,
html.dark .side-menu .el-menu-item.is-active::before {
  background: var(--violet-300);
}
.side-menu .el-menu-item .el-icon,
.side-menu .el-sub-menu__title .el-icon {
  color: inherit;
}
.aside-footer {
  padding: var(--space-6) var(--space-7);
  border-top: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.aside-version {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--fg-tertiary);
}

/* ─── 主内容区 ───────────────────────────── */
.app-main {
  background: var(--bg-canvas);
  min-height: calc(100vh - 64px);
  padding: var(--space-9) var(--space-9);
  overflow-y: auto;
}

/* ─── 响应式 ─────────────────────────────── */
@media (max-width: 768px) {
  .app-header { padding: 0 var(--space-5); }
  .user-meta { display: none; }
  .header-right { gap: var(--space-3); }
  .app-main { padding: var(--space-6); }
}
</style>
