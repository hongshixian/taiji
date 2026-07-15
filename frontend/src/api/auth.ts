import request from './request'

export function register(data: Record<string, unknown>) {
  return request.post('/auth/register', data)
}

export function login(data: { username: string; password: string }) {
  // data: { username, password }
  return request.post('/auth/login', data)
}

export function refreshToken(refreshToken: string) {
  // 不使用 request 实例，避免拦截器循环
  return request.post('/auth/refresh', {}, {
    headers: { Authorization: `Bearer ${refreshToken}` },
  })
}

export function getMe() {
  return request.get('/auth/me')
}

export function listMyTenants() {
  return request.get('/auth/tenants')
}

export function switchTenant(tenantId: number) {
  return request.post('/auth/switch-tenant', { tenant_id: tenantId })
}

export function logout() {
  return request.post('/auth/logout')
}

export function changePassword(oldPassword: string, newPassword: string) {
  return request.put('/auth/password', {
    old_password: oldPassword,
    new_password: newPassword,
  })
}
