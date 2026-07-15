import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  login as loginApi,
  register as registerApi,
  getMe,
  switchTenant as switchTenantApi,
  logout as logoutApi,
} from '../api/auth'
import router from '../router'
import type { User } from '../api/types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const isLoggedIn = ref(!!localStorage.getItem('accessToken'))

  /* 当前用户是否管理员（当前租户 membership 角色） */
  const isAdmin = () => user.value?.role === 'admin'

  /* 当前用户是否平台超级管理员（可跨 tenant 操作） */
  const isSuperuser = computed(() => user.value?.is_superuser === true)

  /* 当前会话指向的租户（来自 JWT claim 对应的 membership） */
  const currentTenant = computed(() => {
    if (!user.value) return null
    if (user.value.current_tenant) {
      return {
        id: user.value.current_tenant.id,
        slug: user.value.current_tenant.slug,
        name: user.value.current_tenant.name,
      }
    }
    return null
  })

  /* 登录时进入的租户 id（用于一键切回） */
  const originalTenantId = computed(() => {
    const stored = localStorage.getItem('originalTenantId')
    return stored ? parseInt(stored, 10) : currentTenant.value?.id ?? null
  })

  async function login(payload: { username: string; password: string }) {
    // payload: { username, password }
    const { data } = await loginApi(payload)
    const { access_token, refresh_token, user: userInfo } = data.data
    localStorage.setItem('accessToken', access_token)
    localStorage.setItem('refreshToken', refresh_token)
    if (userInfo?.current_tenant?.id != null) {
      localStorage.setItem('originalTenantId', String(userInfo.current_tenant.id))
    }
    user.value = userInfo
    isLoggedIn.value = true
    return userInfo
  }

  async function register(username: string, email: string, password: string) {
    const { data } = await registerApi({ username, email, password })
    return data.data
  }

  async function fetchUser() {
    try {
      const { data } = await getMe()
      user.value = data.data
      isLoggedIn.value = true
      if (!localStorage.getItem('originalTenantId') && user.value?.current_tenant?.id != null) {
        localStorage.setItem('originalTenantId', String(user.value.current_tenant.id))
      }
    } catch {
      logout()
    }
  }

  /**
   * 切换当前操作的租户。
   * 拿到新 access token 后替换 localStorage，再 fetchUser() 更新身份。
   * 调用方负责刷新当前页面数据（或全局 window.location.reload）。
   */
  async function switchTenant(tenantId: number) {
    const { data } = await switchTenantApi(tenantId)
    const { access_token } = data.data
    localStorage.setItem('accessToken', access_token)
    // originalTenantId 不更新，保留登录时进入的租户
    await fetchUser()
  }

  /** 切回用户自己原本归属的租户 */
  async function resetTenant() {
    const origId = originalTenantId.value
    if (origId == null) return
    await switchTenant(origId)
  }

  /**
   * 退出登录：先调后端 logout 把 jti 加黑名单，
   * 即使后端失败也清本地状态跳登录页。
   */
  async function logout() {
    try {
      if (localStorage.getItem('accessToken')) {
        await logoutApi()
      }
    } catch {
      // 后端撤销失败也不阻断登出流程
    }
    localStorage.removeItem('accessToken')
    localStorage.removeItem('refreshToken')
    localStorage.removeItem('originalTenantId')
    user.value = null
    isLoggedIn.value = false
    router.push('/login')
  }

  return {
    user, isLoggedIn,
    isAdmin, isSuperuser, currentTenant, originalTenantId,
    login, register, fetchUser, logout,
    switchTenant, resetTenant,
  }
})
