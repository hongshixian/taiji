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
    name: 'Home',
    component: () => import('../views/Home.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/tasks',
    name: 'TaskManagement',
    component: () => import('../views/TaskManagement.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('../views/Settings.vue'),
    meta: { requiresAuth: true },
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

  next()
})

export default router
