import request from './request'

// ─── 租户管理 ──────────────────────────────────────
export function listTenants() {
  return request.get('/superadmin/tenants')
}

export function getTenant(tenantId: number) {
  return request.get(`/superadmin/tenants/${tenantId}`)
}

export function createTenant(data: Record<string, unknown>) {
  return request.post('/superadmin/tenants', data)
}

export function updateTenant(tenantId: number, data: Record<string, unknown>) {
  return request.put(`/superadmin/tenants/${tenantId}`, data)
}

export function deleteTenant(tenantId: number) {
  return request.delete(`/superadmin/tenants/${tenantId}`)
}

// ─── 系统设置 ──────────────────────────────────────
export function listSystemSettings() {
  return request.get('/superadmin/settings')
}

export function updateSystemSettings(data: Record<string, unknown>) {
  return request.put('/superadmin/settings', data)
}

// ─── 超级管理员管理 ────────────────────────────────
export function listSuperusers() {
  return request.get('/superadmin/superusers')
}

export function addSuperuser(identifier: string) {
  return request.post('/superadmin/superusers', { identifier })
}

export function removeSuperuser(userId: number) {
  return request.delete(`/superadmin/superusers/${userId}`)
}

// ─── 超级管理员角色/成员管理辅助 ─────────────────────
export function listSuperadminRoles(tenantId: number | null = null) {
  return request.get('/superadmin/roles', {
    params: tenantId ? { tenant_id: tenantId } : {},
  })
}

export function listTenantMembers(tenantId: number) {
  return request.get(`/superadmin/tenants/${tenantId}/members`)
}

export function addTenantMember(tenantId: number, data: Record<string, unknown>) {
  return request.post(`/superadmin/tenants/${tenantId}/members`, data)
}

export function removeTenantMember(tenantId: number, userId: number) {
  return request.delete(`/superadmin/tenants/${tenantId}/members/${userId}`)
}

// ─── 切换当前操作的租户 ─────────────────────────────
export function switchTenant(tenantId: number) {
  return request.post('/superadmin/switch-tenant', { tenant_id: tenantId })
}
