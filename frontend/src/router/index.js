import { createRouter, createWebHashHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import {
  BENCHMARK_TASK_TYPE,
  RED_TEAM_TASK_TYPE,
  TASK_TYPE_ROUTES,
} from '../constants/taskTypes'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { guest: true },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/Register.vue'),
    meta: { guest: true },
  },
  {
    path: '/',
    name: 'Home',
    component: () => import('../views/Home.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/leaderboard',
    name: 'Leaderboard',
    component: () => import('../views/Leaderboard.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/tasks',
    redirect: TASK_TYPE_ROUTES[BENCHMARK_TASK_TYPE],
    meta: { requiresAuth: true, requiresPermission: 'task:read' },
  },
  {
    path: TASK_TYPE_ROUTES[BENCHMARK_TASK_TYPE],
    name: 'BenchmarkTasks',
    component: () => import('../views/BenchmarkManagement.vue'),
    meta: {
      requiresAuth: true,
      requiresPermission: 'task:read',
      taskType: BENCHMARK_TASK_TYPE,
    },
  },
  {
    path: TASK_TYPE_ROUTES[RED_TEAM_TASK_TYPE],
    name: 'RedTeamTasks',
    component: () => import('../views/RedTeamManagement.vue'),
    meta: {
      requiresAuth: true,
      requiresPermission: 'task:read',
      taskType: RED_TEAM_TASK_TYPE,
    },
  },
  {
    path: '/models',
    name: 'ModelManagement',
    component: () => import('../views/ModelManagement.vue'),
    meta: { requiresAuth: true, requiresPermission: 'model:read' },
  },
  {
    path: '/benchmarks',
    name: 'BenchmarkAssets',
    component: () => import('../views/BenchmarkAssets.vue'),
    meta: { requiresAuth: true, requiresPermission: 'benchmark:read' },
  },
  {
    path: '/users',
    name: 'UserManagement',
    component: () => import('../views/UserManagement.vue'),
    meta: { requiresAuth: true, requiresPermission: 'user:read' },
  },
  {
    path: '/roles',
    name: 'RoleManagement',
    component: () => import('../views/RoleManagement.vue'),
    meta: { requiresAuth: true, requiresPermission: 'role:read' },
  },
  {
    path: '/audit-logs',
    name: 'AuditLogManagement',
    component: () => import('../views/AuditLogManagement.vue'),
    meta: { requiresAuth: true, requiresPermission: 'system:audit' },
  },
  {
    path: '/tenants',
    name: 'TenantManagement',
    component: () => import('../views/TenantManagement.vue'),
    meta: { requiresAuth: true, requiresSuperuser: true },
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('../views/Settings.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/system-settings',
    name: 'SystemSettings',
    component: () => import('../views/SystemSettings.vue'),
    meta: { requiresAuth: true, requiresSuperuser: true },
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore()
  const hasToken = !!localStorage.getItem('accessToken')

  if (to.meta.requiresAuth && !hasToken) {
    return next('/login')
  }

  if (to.meta.guest && hasToken) {
    return next('/')
  }

  if (hasToken && !authStore.user) {
    try {
      await authStore.fetchUser()
    } catch {
      return next('/login')
    }
  }

  if (to.meta.requiresPermission) {
    const perms = new Set(authStore.user?.permissions ?? [])
    if (!perms.has(to.meta.requiresPermission)) {
      return next('/')
    }
  }

  if (to.meta.requiresSuperuser && !authStore.user?.is_superuser) {
    return next('/')
  }

  next()
})

export default router
