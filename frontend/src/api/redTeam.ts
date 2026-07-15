import request from './request'

export const submitRedTeam = (data: Record<string, unknown>) => request.post('/tasks/red-team/', data)
export const getRedTeam = (id: number) => request.get(`/tasks/red-team/${id}`)
export const listRedTeams = (page: number, perPage: number) =>
  request.get('/tasks/red-team/', { params: { page, per_page: perPage } })
export const retryRedTeam = (id: number) => request.post(`/tasks/red-team/${id}/retry`)
export const deleteRedTeam = (id: number) => request.delete(`/tasks/red-team/${id}`)
