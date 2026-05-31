<template>
  <div id="app">
    <el-container v-if="isLoggedIn" class="app-layout">
      <!-- 顶栏 -->
      <el-header class="app-header">
        <div class="header-left">
          <el-icon class="collapse-btn" @click="collapsed = !collapsed">
            <component :is="collapsed ? 'Expand' : 'Fold'" />
          </el-icon>
          <div class="brand">
            <img src="./assets/taiji-logo.svg" alt="taiji" class="brand-logo" />
            <span class="brand-text">太极</span>
          </div>
        </div>

        <div class="header-right">
          <!-- 当前租户 -->
          <TenantSwitcher />

          <!-- 主题切换 -->
          <el-tooltip :content="isDark ? '切换为浅色' : '切换为深色'" placement="bottom">
            <el-icon class="header-icon" @click="toggleTheme">
              <component :is="isDark ? 'Sunny' : 'Moon'" />
            </el-icon>
          </el-tooltip>

          <!-- 通知（占位） -->
          <el-tooltip content="暂无新通知" placement="bottom">
            <el-badge :is-dot="false" class="header-icon-wrap">
              <el-icon class="header-icon"><Bell /></el-icon>
            </el-badge>
          </el-tooltip>

          <!-- 用户菜单 -->
          <el-dropdown trigger="click" @command="handleCommand">
            <div class="user-trigger">
              <el-avatar :size="32" class="user-avatar" :class="{ 'is-superuser': authStore.isSuperuser }">
                {{ avatarInitial }}
              </el-avatar>
              <span class="username">{{ authStore.user?.username }}</span>
              <el-icon class="caret"><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item disabled>
                  <el-tag :type="roleTagType" size="small" effect="light">
                    {{ roleLabel }}
                  </el-tag>
                </el-dropdown-item>
                <el-dropdown-item divided command="settings">
                  <el-icon><Setting /></el-icon> 个人设置
                </el-dropdown-item>
                <el-dropdown-item command="logout">
                  <el-icon><SwitchButton /></el-icon> 退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-container>
        <!-- 侧边栏 -->
        <el-aside :width="collapsed ? '64px' : '210px'" class="app-aside">
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
            <el-sub-menu index="/tasks" v-if="has('task:read')">
              <template #title>
                <el-icon><Tickets /></el-icon>
                <span>任务管理</span>
              </template>
              <el-menu-item :index="TASK_TYPE_ROUTES[WEBPAGE_ANALYSIS_TASK_TYPE]">
                <el-icon><Document /></el-icon>
                <template #title>网页内容分析</template>
              </el-menu-item>
            </el-sub-menu>
            <el-menu-item index="/users" v-if="has('user:read')">
              <el-icon><User /></el-icon>
              <template #title>用户管理</template>
            </el-menu-item>
            <el-menu-item index="/roles" v-if="has('role:read')">
              <el-icon><Key /></el-icon>
              <template #title>角色管理</template>
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
            <span>☯ Taiji v0.1</span>
          </div>
        </el-aside>

        <!-- 主内容区 -->
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
import { TASK_TYPE_ROUTES, WEBPAGE_ANALYSIS_TASK_TYPE } from './constants/taskTypes'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const { has } = usePermission()

const collapsed = ref(window.innerWidth < 900)
const isDark = ref(document.documentElement.classList.contains('dark'))

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
const roleTagType = computed(() => {
  const u = authStore.user
  if (!u) return 'info'
  if (u.is_superuser) return 'danger'
  if (u.role === 'admin') return 'warning'
  return 'info'
})

function toggleTheme() {
  isDark.value = !isDark.value
  document.documentElement.classList.toggle('dark', isDark.value)
  localStorage.setItem('taiji-theme', isDark.value ? 'dark' : 'light')
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
.app-layout {
  height: 100vh;
}

/* ─── 顶栏 ───────────────────────────────── */
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--el-bg-color);
  border-bottom: 1px solid var(--el-border-color-lighter);
  padding: 0 24px;
  height: 60px;
  box-shadow: var(--taiji-shadow-sm);
  z-index: 10;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 20px;
}
.collapse-btn {
  font-size: 20px;
  cursor: pointer;
  color: var(--el-text-color-secondary);
  transition: color 0.2s, transform 0.2s;
}
.collapse-btn:hover {
  color: var(--el-color-primary);
  transform: scale(1.1);
}
.brand {
  display: flex;
  align-items: center;
  gap: 8px;
}
.brand-logo {
  width: 28px;
  height: 28px;
  filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.1));
}
.brand-text {
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 2px;
  color: var(--el-text-color-primary);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 18px;
}
.header-icon,
.header-icon-wrap .header-icon {
  font-size: 18px;
  color: var(--el-text-color-secondary);
  cursor: pointer;
  transition: color 0.2s, transform 0.2s;
}
.header-icon:hover {
  color: var(--taiji-accent);
  transform: scale(1.1);
}
.user-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: var(--taiji-radius-sm);
  transition: background 0.2s;
}
.user-trigger:hover {
  background: var(--el-fill-color-light);
}
.user-avatar {
  background: var(--taiji-gradient-accent);
  color: #fff;
  font-weight: 600;
}
.user-avatar.is-superuser {
  background: linear-gradient(135deg, var(--taiji-accent), #ff7849);
  box-shadow: 0 0 0 2px var(--el-color-danger-light-7);
}
.username {
  color: var(--el-text-color-primary);
  font-size: 14px;
  font-weight: 500;
}
.caret {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

/* ─── 侧边栏 ─────────────────────────────── */
.app-aside {
  background: var(--el-bg-color);
  border-right: 1px solid var(--el-border-color-lighter);
  transition: width 0.3s;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
.side-menu {
  border-right: none !important;
  flex: 1;
}
.side-menu .el-menu-item,
.side-menu .el-sub-menu__title {
  height: 48px;
  line-height: 48px;
  margin: 4px 8px;
  border-radius: var(--taiji-radius-sm);
}
.side-menu .el-sub-menu .el-menu-item {
  margin-left: 12px;
  min-width: 0;
}
.side-menu .el-menu-item.is-active {
  background: var(--el-color-primary-light-9);
  color: var(--taiji-accent);
  font-weight: 500;
}
.side-menu .el-menu-item.is-active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 60%;
  background: var(--taiji-accent);
  border-radius: 0 2px 2px 0;
}
.aside-footer {
  padding: 12px 16px;
  color: var(--el-text-color-placeholder);
  font-size: 12px;
  text-align: center;
  border-top: 1px solid var(--el-border-color-lighter);
}

/* ─── 主内容区 ───────────────────────────── */
.app-main {
  background: var(--el-bg-color-page);
  min-height: calc(100vh - 60px);
  padding: 24px;
  overflow-y: auto;
}

/* ─── 响应式 ─────────────────────────────── */
@media (max-width: 768px) {
  .app-header { padding: 0 12px; }
  .username { display: none; }
  .header-right { gap: 12px; }
  .app-main { padding: 12px; }
}
</style>
