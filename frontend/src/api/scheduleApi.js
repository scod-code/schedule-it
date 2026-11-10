import axios from 'axios'

const api = axios.create({ baseURL: '' }) // vite proxy handles /api

export const generateSchedule = (data) => api.post('/api/generate', data)
export const getJob = (jobId) => api.get(`/api/jobs/${jobId}`)
export const createCheckout = (jobId) => api.post(`/api/checkout/${jobId}`)
export const downloadUrl = (jobId, format, teamName) =>
  teamName
    ? `/api/download/${jobId}/ics/${encodeURIComponent(teamName)}`
    : `/api/download/${jobId}/${format}`
