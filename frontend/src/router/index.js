import { createRouter, createWebHashHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

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
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/history',
    name: 'TaskHistory',
    component: () => import('../views/TaskHistory.vue'),
    meta: { requiresAuth: true },
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

// 导航守卫
router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore()
  const hasToken = !!localStorage.getItem('accessToken')

  if (to.meta.requiresAuth && !hasToken) {
    return next('/login')
  }

  if (to.meta.guest && hasToken) {
    return next('/')
  }

  // 有 token 但用户信息未加载，先获取
  if (hasToken && !authStore.user) {
    try {
      await authStore.fetchUser()
    } catch {
      return next('/login')
    }
  }

  next()
})

export default router