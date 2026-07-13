import request from './request'

export const listModels = (page = 1, perPage = 50, includeInactive = false) =>
  request.get('/models/', { params: { page, per_page: perPage, include_inactive: includeInactive } })

export const getModel = (id) => request.get(`/models/${id}`)

export const createModel = (data) => request.post('/models/', data)

export const updateModel = (id, data) => request.put(`/models/${id}`, data)

export const deleteModel = (id) => request.delete(`/models/${id}`)

export const testModel = (id) => request.post(`/models/${id}/test`)
