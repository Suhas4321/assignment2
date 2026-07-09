import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import * as api from '../../services/api'
import { mergeFormFromAgent, setCurrentInteractionId } from './interactionSlice'

const SESSION_ID = 'hcp-log-session'

export const sendChatMessage = createAsyncThunk(
  'chat/send',
  async ({ message, hcpId, repId }, { dispatch, rejectWithValue }) => {
    try {
      const res = await api.chatWithAgent({
        message,
        session_id: SESSION_ID,
        rep_id: repId || 'REP-001',
        hcp_id: hcpId || null,
      })
      if (res.form_data) {
        dispatch(mergeFormFromAgent(res.form_data))
      }
      if (res.interaction_id) {
        dispatch(setCurrentInteractionId(res.interaction_id))
      }
      return res
    } catch (e) {
      return rejectWithValue(e.response?.data?.detail || e.message)
    }
  }
)

export const resetChat = createAsyncThunk('chat/reset', async () => {
  await api.resetAgentChat(SESSION_ID)
  return true
})

const chatSlice = createSlice({
  name: 'chat',
  initialState: {
    messages: [
      {
        id: 'welcome',
        role: 'assistant',
        content:
          'Log interaction details here (e.g., "Met Dr. Smith, discussed Product X efficacy, positive sentiment, shared brochure") or ask for help.',
      },
    ],
    status: 'idle', // idle | streaming | error
    toolsUsed: [],
    error: null,
  },
  reducers: {
    clearError(state) {
      state.error = null
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(sendChatMessage.pending, (state, action) => {
        state.status = 'streaming'
        state.error = null
        state.messages.push({
          id: `u-${Date.now()}`,
          role: 'user',
          content: action.meta.arg.message,
        })
      })
      .addCase(sendChatMessage.fulfilled, (state, action) => {
        state.status = 'idle'
        const tools = (action.payload.tool_calls || []).map((t) => t.tool)
        state.toolsUsed = [...new Set([...(state.toolsUsed || []), ...tools])]
        const logged =
          tools.includes('log_interaction') || Boolean(action.payload.interaction_id)
        let content = action.payload.reply || ''
        // Match assignment demo: clear success copy when form was filled from chat
        if (logged && action.payload.form_data) {
          const fd = action.payload.form_data
          content =
            `Interaction logged successfully! The details (HCP Name${
              fd.hcp_name ? `: ${fd.hcp_name}` : ''
            }, Date, Sentiment${fd.sentiment ? `: ${fd.sentiment}` : ''}, and Materials) have been automatically populated based on your summary. Would you like me to suggest a specific follow-up action, such as scheduling a meeting?\n\n${content}`
        }
        state.messages.push({
          id: `a-${Date.now()}`,
          role: 'assistant',
          content,
          tools,
          isSuccess: logged,
        })
      })
      .addCase(sendChatMessage.rejected, (state, action) => {
        state.status = 'error'
        state.error = action.payload || 'Chat failed'
        state.messages.push({
          id: `e-${Date.now()}`,
          role: 'assistant',
          content: `Sorry — ${state.error}`,
          isError: true,
        })
      })
      .addCase(resetChat.fulfilled, (state) => {
        state.messages = [
          {
            id: 'welcome',
            role: 'assistant',
            content:
              'Log interaction details here (e.g., "Met Dr. Smith, discussed Product X efficacy, positive sentiment, shared brochure") or ask for help.',
          },
        ]
        state.toolsUsed = []
        state.status = 'idle'
        state.error = null
      })
  },
})

export const { clearError } = chatSlice.actions
export default chatSlice.reducer
