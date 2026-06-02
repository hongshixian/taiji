import request from './request'

export function listTasks(page = 1, perPage = 20) {
  return request.get('/tasks/', { params: { page, per_page: perPage } })
}

export function getTaskLogs(taskId) {
  return request.get(`/tasks/${taskId}/logs`)
}
