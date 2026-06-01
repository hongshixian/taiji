import request from './request'

export function submitWebpageAnalysis(url) {
  return request.post('/tasks/webpage-analysis/', { url })
}

export function getWebpageAnalysis(taskId) {
  return request.get(`/tasks/webpage-analysis/${taskId}`)
}

export function listWebpageAnalyses(page = 1, perPage = 20) {
  return request.get('/tasks/webpage-analysis/', { params: { page, per_page: perPage } })
}

export function retryWebpageAnalysis(taskId) {
  return request.post(`/tasks/webpage-analysis/${taskId}/retry`)
}

export function deleteWebpageAnalysis(taskId) {
  return request.delete(`/tasks/webpage-analysis/${taskId}`)
}
