import request from './request'

// ─── 用户管理 ──────────────────────────────────────
export function listUsers(page = 1, perPage = 20) {
  return request.get('/admin/users', { params: { page, per_page: perPage } })
}

export function getUser(userId: number) {
  return request.get(`/admin/users/${userId}`)
}

export function createUser(data: Record<string, unknown>) {
  return request.post('/admin/users', data)
}

export function updateUser(userId: number, data: Record<string, unknown>) {
  return request.put(`/admin/users/${userId}`, data)
}

export function deleteUser(userId: number) {
  return request.delete(`/admin/users/${userId}`)
}

// ─── 角色管理 (RBAC) ──────────────────────────────
export function listRoles() {
  return request.get('/admin/roles')
}
