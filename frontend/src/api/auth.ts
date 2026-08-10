import request from './request'

export const LOGIN_URL = '/api/v1/auth/login'
export const REGISTER_URL = '/api/v1/auth/register'

export function getMe() {
  return request.get('/auth/me')
}

export function switchTenant(tenantId: string) {
  return request.post('/auth/switch-tenant', { tenant_id: tenantId })
}

export function logout() {
  return request.post('/auth/logout')
}

export function getAccountManagementUrl() {
  return request.put('/auth/password')
}
