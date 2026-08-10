import axios, { type AxiosError, type AxiosInstance } from 'axios'

let csrfToken: string | null = null

export function setCsrfToken(value?: string | null) {
  csrfToken = value || null
}

const request: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  withCredentials: true,
})

request.interceptors.request.use((config) => {
  const method = (config.method || 'get').toLowerCase()
  if (csrfToken && !['get', 'head', 'options', 'trace'].includes(method)) {
    config.headers['X-CSRF-Token'] = csrfToken
  }
  return config
})

let handlingExpiredSession = false

request.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    if (error.response?.status === 401 && !handlingExpiredSession) {
      handlingExpiredSession = true
      setCsrfToken(null)
      const { useAuthStore } = await import('../stores/auth')
      useAuthStore().clearSession()
      if (!['#/login', '#/register'].some((path) => window.location.hash.startsWith(path))) {
        window.location.hash = '#/login'
      }
      window.setTimeout(() => { handlingExpiredSession = false }, 0)
    }
    return Promise.reject(error)
  },
)

export default request
