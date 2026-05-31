import request from './request'

// ─── 租户管理 ──────────────────────────────────────
export function listTenants() {
  return request.get('/superadmin/tenants')
}

export function getTenant(tenantId) {
  return request.get(`/superadmin/tenants/${tenantId}`)
}

export function createTenant(data) {
  return request.post('/superadmin/tenants', data)
}

export function updateTenant(tenantId, data) {
  return request.put(`/superadmin/tenants/${tenantId}`, data)
}

export function deleteTenant(tenantId) {
  return request.delete(`/superadmin/tenants/${tenantId}`)
}

// ─── 切换当前操作的租户 ─────────────────────────────
export function switchTenant(tenantId) {
  return request.post('/superadmin/switch-tenant', { tenant_id: tenantId })
}
