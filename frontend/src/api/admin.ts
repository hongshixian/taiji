import request from './request'

// ─── 用户管理 ──────────────────────────────────────
export function listUsers(page = 1, perPage = 20) {
  return request.get('/admin/users', { params: { page, per_page: perPage } })
}

export function getUser(userId) {
  return request.get(`/admin/users/${userId}`)
}

export function createUser(data) {
  return request.post('/admin/users', data)
}

export function updateUser(userId, data) {
  return request.put(`/admin/users/${userId}`, data)
}

export function deleteUser(userId) {
  return request.delete(`/admin/users/${userId}`)
}

// ─── 角色管理 (RBAC) ──────────────────────────────
export function listRoles() {
  return request.get('/admin/roles')
}

export function listAllPermissions() {
  return request.get('/admin/roles/permissions')
}

export function getRole(roleId) {
  return request.get(`/admin/roles/${roleId}`)
}

export function createRole(data) {
  return request.post('/admin/roles', data)
}

export function updateRole(roleId, data) {
  return request.put(`/admin/roles/${roleId}`, data)
}

export function deleteRole(roleId) {
  return request.delete(`/admin/roles/${roleId}`)
}
