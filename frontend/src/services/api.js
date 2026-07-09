import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
})

// ─── HCPs ────────────────────────────────────────────────────────────────────
export const searchHcps = (params = {}) => api.get('/hcps', { params }).then((r) => r.data)
export const getHcp = (id) => api.get(`/hcps/${id}`).then((r) => r.data)
export const listHcps = () => api.get('/hcps').then((r) => r.data)

// ─── Interactions ────────────────────────────────────────────────────────────
export const createInteraction = (data) =>
  api.post('/interactions', data).then((r) => r.data)
export const updateInteraction = (id, data) =>
  api.patch(`/interactions/${id}`, data).then((r) => r.data)
export const getInteraction = (id) =>
  api.get(`/interactions/${id}`).then((r) => r.data)
export const listInteractions = (params = {}) =>
  api.get('/interactions', { params }).then((r) => r.data)
export const getHcpInteractions = (hcpId, params = {}) =>
  api.get(`/hcps/${hcpId}/interactions`, { params }).then((r) => r.data)

// ─── Follow-ups ──────────────────────────────────────────────────────────────
export const createFollowUp = (data) =>
  api.post('/follow-ups', data).then((r) => r.data)
export const listFollowUps = (params = {}) =>
  api.get('/follow-ups', { params }).then((r) => r.data)
export const suggestFollowUps = (data) =>
  api.post('/interactions/suggest-followups', data).then((r) => r.data)

// ─── Agent ───────────────────────────────────────────────────────────────────
export const chatWithAgent = (data) =>
  api.post('/agent/chat', data).then((r) => r.data)
export const resetAgentChat = (sessionId = 'default') =>
  api.post(`/agent/chat/reset?session_id=${encodeURIComponent(sessionId)}`).then((r) => r.data)
export const listAgentTools = () => api.get('/agent/tools').then((r) => r.data)

export const healthCheck = () => api.get('/health').then((r) => r.data)

export default api
