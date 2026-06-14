import request from './request'

export const submitBenchmark = (data) => request.post('/tasks/benchmark/', data)
export const getBenchmark = (id) => request.get(`/tasks/benchmark/${id}`)
export const listBenchmarks = (page, perPage) =>
  request.get('/tasks/benchmark/', { params: { page, per_page: perPage } })
export const retryBenchmark = (id) => request.post(`/tasks/benchmark/${id}/retry`)
export const deleteBenchmark = (id) => request.delete(`/tasks/benchmark/${id}`)
