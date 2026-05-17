import { defineStore } from 'pinia'
import { ref } from 'vue'
import { login as loginApi, register as registerApi, getMe } from '../api/auth'
import router from '../router'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const isLoggedIn = ref(!!localStorage.getItem('accessToken'))

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

  function logout() {
    localStorage.removeItem('accessToken')
    localStorage.removeItem('refreshToken')
    user.value = null
    isLoggedIn.value = false
    router.push('/login')
  }

  return { user, isLoggedIn, login, register, fetchUser, logout }
})