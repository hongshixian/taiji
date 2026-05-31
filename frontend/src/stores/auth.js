import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  login as loginApi,
  register as registerApi,
  getMe,
  logout as logoutApi,
} from '../api/auth'
import router from '../router'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const isLoggedIn = ref(!!localStorage.getItem('accessToken'))

  /* 当前用户是否管理员 */
  const isAdmin = () => user.value?.role === 'admin'

  async function login(username, password) {
    const { data } = await loginApi({ username, password })
    const { access_token, refresh_token, user: userInfo } = data.data
    localStorage.setItem('accessToken', access_token)
    localStorage.setItem('refreshToken', refresh_token)
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
    } catch {
      logout()
    }
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
    user.value = null
    isLoggedIn.value = false
    router.push('/login')
  }

  return { user, isLoggedIn, isAdmin, login, register, fetchUser, logout }
})
