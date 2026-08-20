import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import router from '../router'
import {
  getMe,
  LOGIN_URL,
  logout as logoutApi,
  REGISTER_URL,
  switchTenant as switchTenantApi,
} from '../api/auth'
import { setCsrfToken } from '../api/request'
import type { User } from '../api/types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const initialized = ref(false)
  const initializing = ref<Promise<void> | null>(null)

  const isLoggedIn = computed(() => user.value !== null)
  const isAdmin = computed(() => user.value?.role === 'tenant_admin')
  const isSuperuser = computed(() => user.value?.is_superuser === true)
  const currentTenant = computed(() => user.value?.current_tenant ?? null)
  const tenants = computed(() => user.value?.tenants ?? [])

  function applyUser(value: User) {
    user.value = value
    setCsrfToken(value.csrf_token)
  }

  function clearSession() {
    user.value = null
    setCsrfToken(null)
  }

  async function fetchUser() {
    const { data } = await getMe()
    applyUser(data.data)
    return data.data as User
  }

  async function initialize() {
    if (initialized.value) return
    if (initializing.value) return initializing.value
    initializing.value = fetchUser()
      .then(() => undefined)
      .catch(() => { clearSession() })
      .finally(() => {
        initialized.value = true
        initializing.value = null
      })
    return initializing.value
  }

  function login() {
    window.location.assign(LOGIN_URL)
  }

  function register() {
    window.location.assign(REGISTER_URL)
  }

  async function switchTenant(tenantId: number) {
    const { data } = await switchTenantApi(tenantId)
    setCsrfToken(data.data.csrf_token)
    await fetchUser()
  }

  async function logout() {
    let logoutUrl: string | undefined
    try {
      const { data } = await logoutApi()
      logoutUrl = data.data?.logout_url
    } catch {
      // Local state must still be cleared when the server session has expired.
    }
    clearSession()
    initialized.value = true
    if (logoutUrl) {
      window.location.assign(logoutUrl)
    } else {
      await router.push('/login')
    }
  }

  return {
    user,
    initialized,
    isLoggedIn,
    isAdmin,
    isSuperuser,
    currentTenant,
    tenants,
    initialize,
    fetchUser,
    clearSession,
    login,
    register,
    logout,
    switchTenant,
  }
})
