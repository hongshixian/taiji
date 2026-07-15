import axios, {
  type AxiosError,
  type AxiosInstance,
  type InternalAxiosRequestConfig,
} from 'axios'
import { useAuthStore } from '../stores/auth'

const request: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
})

// 请求拦截器：自动附带 access token
request.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('accessToken')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

// 响应拦截器：401 自动刷新 token
let isRefreshing = false
type QueueItem = { resolve: (token: string) => void; reject: (err: unknown) => void }
let failedQueue: QueueItem[] = []

function processQueue(error: unknown, token: string | null = null) {
  failedQueue.forEach((prom) => {
    if (error) prom.reject(error)
    else if (token) prom.resolve(token)
  })
  failedQueue = []
}

request.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<{ code?: number }>) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }
    const errCode = error.response?.data?.code

    // TOKEN_REVOKED (30006)：直接跳登录，避免循环
    if (errCode === 30006) {
      localStorage.removeItem('accessToken')
      localStorage.removeItem('refreshToken')
      if (!window.location.hash.startsWith('#/login')) {
        window.location.hash = '#/login'
      }
      return Promise.reject(error)
    }

    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error)
    }

    if (isRefreshing) {
      return new Promise<string>((resolve, reject) => {
        failedQueue.push({ resolve, reject })
      })
        .then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`
          return request(originalRequest)
        })
        .catch((err) => Promise.reject(err))
    }

    originalRequest._retry = true
    isRefreshing = true

    const refreshToken = localStorage.getItem('refreshToken')
    if (!refreshToken) {
      useAuthStore().logout()
      window.location.hash = '#/login'
      return Promise.reject(error)
    }

    try {
      const { data } = await axios.post(
        '/api/v1/auth/refresh',
        {},
        { headers: { Authorization: `Bearer ${refreshToken}` } },
      )
      const newAccessToken = data.data.access_token
      localStorage.setItem('accessToken', newAccessToken)
      processQueue(null, newAccessToken)
      originalRequest.headers.Authorization = `Bearer ${newAccessToken}`
      return request(originalRequest)
    } catch (refreshError) {
      processQueue(refreshError, null)
      useAuthStore().logout()
      window.location.hash = '#/login'
      return Promise.reject(refreshError)
    } finally {
      isRefreshing = false
    }
  },
)

export default request
