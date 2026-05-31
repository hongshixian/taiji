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

// ─── 系统设置 ──────────────────────────────────────
export function listSystemSettings() {
  return request.get('/superadmin/settings')
}

export function updateSystemSettings(data) {
  return request.put('/superadmin/settings', data)
}

// ─── 超级管理员管理 ────────────────────────────────
export function listSuperusers() {
  return request.get('/superadmin/superusers')
}

export function addSuperuser(identifier) {
  return request.post('/superadmin/superusers', { identifier })
}

export function removeSuperuser(userId) {
  return request.delete(`/superadmin/superusers/${userId}`)
}

// ─── 超级管理员角色/成员管理辅助 ─────────────────────
export function listSuperadminRoles() {
  return request.get('/superadmin/roles')
}

export function listTenantMembers(tenantId) {
  return request.get(`/superadmin/tenants/${tenantId}/members`)
}

export function addTenantMember(tenantId, data) {
  return request.post(`/superadmin/tenants/${tenantId}/members`, data)
}

export function removeTenantMember(tenantId, userId) {
  return request.delete(`/superadmin/tenants/${tenantId}/members/${userId}`)
}

// ─── 切换当前操作的租户 ─────────────────────────────
export function switchTenant(tenantId) {
  return request.post('/superadmin/switch-tenant', { tenant_id: tenantId })
}
