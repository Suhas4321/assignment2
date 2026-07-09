import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import * as api from '../../services/api'

const today = () => new Date().toISOString().slice(0, 10)
const nowTime = () =>
  new Date().toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })

const emptyForm = () => ({
  hcp_id: null,
  hcp_name: '',
  rep_id: 'REP-001',
  interaction_type: 'Meeting',
  interaction_date: today(),
  interaction_time: nowTime(),
  attendees: [],
  topics_discussed: '',
  materials_shared: [],
  samples_distributed: [],
  products_discussed: [],
  sentiment: 'Neutral',
  outcomes: '',
  follow_up_actions: '',
  summary: '',
})

export const fetchHcps = createAsyncThunk('interaction/fetchHcps', async (q) => {
  return api.searchHcps(q ? { q } : {})
})

export const saveInteraction = createAsyncThunk(
  'interaction/save',
  async ({ id, data }, { rejectWithValue }) => {
    try {
      if (id) return await api.updateInteraction(id, data)
      return await api.createInteraction(data)
    } catch (e) {
      return rejectWithValue(e.response?.data?.detail || e.message)
    }
  }
)

export const loadHcpHistory = createAsyncThunk(
  'interaction/history',
  async (hcpId) => api.getHcpInteractions(hcpId)
)

export const loadSuggestions = createAsyncThunk(
  'interaction/suggestions',
  async (payload) => api.suggestFollowUps(payload)
)

const interactionSlice = createSlice({
  name: 'interaction',
  initialState: {
    form: emptyForm(),
    hcps: [],
    hcpSearchLoading: false,
    history: [],
    suggestions: [
      'Schedule follow-up meeting in 2 weeks',
      'Send OncoBoost Phase III PDF',
      'Add HCP to advisory board invite list',
    ],
    currentInteractionId: null,
    status: 'idle', // idle | saving | saved | error
    error: null,
    toast: null,
  },
  reducers: {
    setField(state, action) {
      const { field, value } = action.payload
      state.form[field] = value
    },
    setForm(state, action) {
      state.form = { ...state.form, ...action.payload }
    },
    mergeFormFromAgent(state, action) {
      const data = action.payload || {}
      // Only overwrite fields that agent provided
      Object.entries(data).forEach(([k, v]) => {
        if (v === null || v === undefined || v === '') return
        if (k in state.form) state.form[k] = v
      })
      if (data.hcp_id) state.form.hcp_id = data.hcp_id
      if (data.hcp_name) state.form.hcp_name = data.hcp_name
    },
    selectHcp(state, action) {
      const hcp = action.payload
      state.form.hcp_id = hcp.id
      state.form.hcp_name = hcp.name
    },
    addListItem(state, action) {
      const { field, value } = action.payload
      if (!value?.trim()) return
      if (!Array.isArray(state.form[field])) state.form[field] = []
      if (!state.form[field].includes(value.trim())) {
        state.form[field].push(value.trim())
      }
    },
    removeListItem(state, action) {
      const { field, value } = action.payload
      state.form[field] = (state.form[field] || []).filter((x) => x !== value)
    },
    appendFollowUp(state, action) {
      const line = action.payload
      const current = state.form.follow_up_actions || ''
      state.form.follow_up_actions = current
        ? `${current}\n• ${line}`
        : `• ${line}`
    },
    resetForm(state) {
      state.form = emptyForm()
      state.currentInteractionId = null
      state.status = 'idle'
      state.error = null
      state.history = []
    },
    setCurrentInteractionId(state, action) {
      state.currentInteractionId = action.payload
    },
    clearToast(state) {
      state.toast = null
    },
    setToast(state, action) {
      state.toast = action.payload
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchHcps.pending, (state) => {
        state.hcpSearchLoading = true
      })
      .addCase(fetchHcps.fulfilled, (state, action) => {
        state.hcpSearchLoading = false
        state.hcps = action.payload
      })
      .addCase(fetchHcps.rejected, (state) => {
        state.hcpSearchLoading = false
      })
      .addCase(saveInteraction.pending, (state) => {
        state.status = 'saving'
        state.error = null
      })
      .addCase(saveInteraction.fulfilled, (state, action) => {
        state.status = 'saved'
        state.currentInteractionId = action.payload.id
        state.toast = {
          type: 'success',
          message: `Interaction #${action.payload.id} saved successfully`,
        }
      })
      .addCase(saveInteraction.rejected, (state, action) => {
        state.status = 'error'
        state.error = action.payload || 'Failed to save'
        state.toast = { type: 'error', message: state.error }
      })
      .addCase(loadHcpHistory.fulfilled, (state, action) => {
        state.history = action.payload
      })
      .addCase(loadSuggestions.fulfilled, (state, action) => {
        state.suggestions = action.payload.suggestions || state.suggestions
      })
  },
})

export const {
  setField,
  setForm,
  mergeFormFromAgent,
  selectHcp,
  addListItem,
  removeListItem,
  appendFollowUp,
  resetForm,
  setCurrentInteractionId,
  clearToast,
  setToast,
} = interactionSlice.actions

export default interactionSlice.reducer
