import request from './request'

export const submitBenchmark = (data: Record<string, unknown>) => request.post('/tasks/benchmark/', data)
export const getBenchmark = (id: number) => request.get(`/tasks/benchmark/${id}`)
export const listBenchmarks = (page: number, perPage: number) =>
  request.get('/tasks/benchmark/', { params: { page, per_page: perPage } })
// 按状态统计当前租户的 benchmark 任务数量（页面顶部指标用，全局口径）
export const getBenchmarkStats = () => request.get('/tasks/benchmark/stats')
// 点击样本方块时懒加载单条样本预览（samples_preview 不随列表/详情返回）
export const getSamplePreview = (taskId: number, sampleId: string | number) =>
  request.get(`/tasks/benchmark/${taskId}/samples/${sampleId}`)
export const retryBenchmark = (id: number) => request.post(`/tasks/benchmark/${id}/retry`)
export const deleteBenchmark = (id: number) => request.delete(`/tasks/benchmark/${id}`)

// 引擎无关的元数据（前端 dynamic form 用）
export const listBenchmarkSuites = () => request.get('/benchmarks/suites')
export const getExecutionSchema = () => request.get('/benchmarks/execution-schema')

export const stopBenchmark = (id: number) => request.post(`/tasks/benchmark/${id}/stop`)
