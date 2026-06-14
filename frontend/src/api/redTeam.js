import request from './request'

export const submitRedTeam = (data) => request.post('/tasks/red-team/', data)
export const getRedTeam = (id) => request.get(`/tasks/red-team/${id}`)
export const listRedTeams = (page, perPage) =>
  request.get('/tasks/red-team/', { params: { page, per_page: perPage } })
export const retryRedTeam = (id) => request.post(`/tasks/red-team/${id}/retry`)
export const deleteRedTeam = (id) => request.delete(`/tasks/red-team/${id}`)
