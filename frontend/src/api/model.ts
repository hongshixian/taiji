import request from './request'

export const listModels = (page = 1, perPage = 50, includeInactive = false) =>
  request.get('/models/', { params: { page, per_page: perPage, include_inactive: includeInactive } })

export const getModel = (id: number) => request.get(`/models/${id}`)

export const createModel = (data: Record<string, unknown>) => request.post('/models/', data)

export const updateModel = (id: number, data: Record<string, unknown>) => request.put(`/models/${id}`, data)

export const deleteModel = (id: number) => request.delete(`/models/${id}`)

export const testModel = (id: number) => request.post(`/models/${id}/test`)
