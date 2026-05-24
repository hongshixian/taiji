import request from './request'

export function submitAnalysis(url) {
  return request.post('/analyze/', { url })
}

export function getAnalysis(taskId) {
  return request.get(`/analyze/${taskId}`)
}

export function listAnalyses(page = 1, perPage = 20) {
  return request.get('/analyze/', { params: { page, per_page: perPage } })
}
export function retryAnalysis(taskId) {
  return request.post(`/analyze/${taskId}/retry`)
}
