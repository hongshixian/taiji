import request from './request'

export function submitCsvQuality(taskName, file) {
  const formData = new FormData()
  formData.append('task_name', taskName)
  formData.append('file', file)
  return request.post('/tasks/csv-quality/', formData)
}

export function getCsvQuality(taskId) {
  return request.get(`/tasks/csv-quality/${taskId}`)
}

export function listCsvQuality(page = 1, perPage = 20) {
  return request.get('/tasks/csv-quality/', { params: { page, per_page: perPage } })
}

export function retryCsvQuality(taskId) {
  return request.post(`/tasks/csv-quality/${taskId}/retry`)
}

export function deleteCsvQuality(taskId) {
  return request.delete(`/tasks/csv-quality/${taskId}`)
}
