import request from './request'

// 获取用户列表
export function listUsers(page = 1, perPage = 20) {
  return request.get('/admin/users', { params: { page, per_page: perPage } })
}

// 获取单个用户
export function getUser(userId) {
  return request.get(`/admin/users/${userId}`)
}

// 创建用户
export function createUser(data) {
  return request.post('/admin/users', data)
}

// 更新用户
export function updateUser(userId, data) {
  return request.put(`/admin/users/${userId}`, data)
}

// 删除用户
export function deleteUser(userId) {
  return request.delete(`/admin/users/${userId}`)
}
