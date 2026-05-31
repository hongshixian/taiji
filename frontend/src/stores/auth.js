import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  login as loginApi,
  register as registerApi,
  getMe,
  logout as logoutApi,
} from '../api/auth'
import { switchTenant as switchTenantApi } from '../api/superadmin'
import router from '../router'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const isLoggedIn = ref(!!localStorage.getItem('accessToken'))

  /* 当前用户是否管理员（角色） */
  const isAdmin = () => user.value?.role === 'admin'

  /* 当前用户是否平台超级管理员（可跨 tenant 操作） */
  const isSuperuser = computed(() => user.value?.is_superuser === true)

  /* 当前会话指向的租户（superuser 切换后会变；后端 /me 通过 current_tenant
     字段提供，反映 JWT claim 中的 tenant_id；登录时 user_to_dict 的 tenant_*
     字段是用户真实归属租户，用作 fallback） */
  const currentTenant = computed(() => {
    if (!user.value) return null
    if (user.value.current_tenant) {
      return {
        id: user.value.current_tenant.id,
        slug: user.value.current_tenant.slug,
        name: user.value.current_tenant.name,
        plan: user.value.current_tenant.plan,
      }
    }
    // fallback：登录响应里只有 tenant_* 字段
    return {
      id: user.value.tenant_id,
      slug: user.value.tenant_slug,
      name: user.value.tenant_name,
    }
  })

  /* 用户自己原始归属的租户 id（不随 switchTenant 改变） */
  const originalTenantId = computed(() => {
    const stored = localStorage.getItem('originalTenantId')
    return stored ? parseInt(stored, 10) : user.value?.tenant_id ?? null
  })

  async function login(payload) {
    // payload: { username, password, tenant_slug? }
    const { data } = await loginApi(payload)
    const { access_token, refresh_token, user: userInfo } = data.data
    localStorage.setItem('accessToken', access_token)
    localStorage.setItem('refreshToken', refresh_token)
    // 记录用户真实归属的 tenant，便于"切回"
    if (userInfo?.tenant_id != null) {
      localStorage.setItem('originalTenantId', String(userInfo.tenant_id))
    }
    user.value = userInfo
    isLoggedIn.value = true
    return userInfo
  }

  async function register(username, email, password) {
    const { data } = await registerApi({ username, email, password })
    return data.data
  }

  async function fetchUser() {
    try {
      const { data } = await getMe()
      user.value = data.data
      isLoggedIn.value = true
      // 兜底：刷新页面后若 localStorage 没记，按当前 user.tenant_id 填一次
      if (!localStorage.getItem('originalTenantId') && user.value?.tenant_id != null) {
        localStorage.setItem('originalTenantId', String(user.value.tenant_id))
      }
    } catch {
      logout()
    }
  }

  /**
   * 超级管理员切换当前操作的租户。
   * 拿到新 access token 后替换 localStorage，再 fetchUser() 更新身份。
   * 调用方负责刷新当前页面数据（或全局 window.location.reload）。
   */
  async function switchTenant(tenantId) {
    const { data } = await switchTenantApi(tenantId)
    const { access_token } = data.data
    localStorage.setItem('accessToken', access_token)
    // 注意：originalTenantId 不更新，保留用户真实归属
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
