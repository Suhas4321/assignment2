import { useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import HCPSearch from '../HCPSearch/HCPSearch'
import {
  setField,
  addListItem,
  removeListItem,
  appendFollowUp,
  saveInteraction,
  resetForm,
  loadSuggestions,
} from '../../store/slices/interactionSlice'
import './LogInteractionForm.css'

const TYPES = ['Meeting', 'Call', 'Email', 'Conference', 'Visit', 'Other']
const SENTIMENTS = [
  { value: 'Positive', emoji: '😊', color: '#16a34a' },
  { value: 'Neutral', emoji: '😐', color: '#d97706' },
  { value: 'Negative', emoji: '😞', color: '#dc2626' },
]

function ListEditor({ label, field, placeholder, buttonLabel }) {
  const dispatch = useDispatch()
  const items = useSelector((s) => s.interaction.form[field]) || []
  const [draft, setDraft] = useState('')

  const add = () => {
    if (!draft.trim()) return
    dispatch(addListItem({ field, value: draft }))
    setDraft('')
  }

  return (
    <div className="list-editor">
      <div className="list-editor-head">
        <span className="list-label">{label}</span>
        <div className="list-add">
          <input
            className="input input-sm"
            placeholder={placeholder}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), add())}
          />
          <button type="button" className="btn btn-secondary btn-sm" onClick={add}>
            {buttonLabel}
          </button>
        </div>
      </div>
      <div className="chip-row">
        {items.length === 0 && <span className="list-empty">None added.</span>}
        {items.map((item) => (
          <button
            type="button"
            key={item}
            className="chip chip-removable"
            onClick={() => dispatch(removeListItem({ field, value: item }))}
            title="Remove"
          >
            {item} ×
          </button>
        ))}
      </div>
    </div>
  )
}

export default function LogInteractionForm() {
  const dispatch = useDispatch()
  const { form, status, currentInteractionId, suggestions } = useSelector((s) => s.interaction)

  const onChange = (field) => (e) =>
    dispatch(setField({ field, value: e.target.value }))

  const onSave = () => {
    if (!form.hcp_id) {
      alert('Please select an HCP first.')
      return
    }
    const payload = {
      hcp_id: form.hcp_id,
      rep_id: form.rep_id || 'REP-001',
      interaction_type: form.interaction_type,
      interaction_date: form.interaction_date,
      interaction_time: form.interaction_time,
      attendees: form.attendees,
      topics_discussed: form.topics_discussed,
      materials_shared: form.materials_shared,
      samples_distributed: form.samples_distributed,
      products_discussed: form.products_discussed,
      sentiment: form.sentiment,
      outcomes: form.outcomes,
      follow_up_actions: form.follow_up_actions,
      summary: form.summary || null,
    }
    dispatch(
      saveInteraction({
        id: currentInteractionId,
        data: payload,
      })
    )
  }

  const refreshSuggestions = () => {
    dispatch(
      loadSuggestions({
        hcp_name: form.hcp_name,
        topics_discussed: form.topics_discussed,
        outcomes: form.outcomes,
      })
    )
  }

  return (
    <div className="card form-card">
      <div className="card-header form-card-header">
        <span>Interaction Details</span>
        {currentInteractionId && (
          <span className="editing-badge">Editing #{currentInteractionId}</span>
        )}
      </div>

      {/* Scrolls independently of the AI chat panel */}
      <div className="form-scroll">
        <div className="field-row">
          <HCPSearch />
          <div className="field">
            <label>Interaction Type</label>
            <select
              className="select"
              value={form.interaction_type}
              onChange={onChange('interaction_type')}
            >
              {TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="field-row">
          <div className="field">
            <label>Date</label>
            <input
              type="date"
              className="input"
              value={form.interaction_date || ''}
              onChange={onChange('interaction_date')}
            />
          </div>
          <div className="field">
            <label>Time</label>
            <input
              type="time"
              className="input"
              value={form.interaction_time || ''}
              onChange={onChange('interaction_time')}
            />
          </div>
        </div>

        <div className="field">
          <label>Attendees</label>
          <input
            className="input"
            placeholder="Enter names separated by commas..."
            value={(form.attendees || []).join(', ')}
            onChange={(e) =>
              dispatch(
                setField({
                  field: 'attendees',
                  value: e.target.value
                    .split(',')
                    .map((s) => s.trim())
                    .filter(Boolean),
                })
              )
            }
          />
        </div>

        <div className="field">
          <label>Topics Discussed</label>
          <textarea
            className="textarea"
            placeholder="Enter key discussion points..."
            value={form.topics_discussed || ''}
            onChange={onChange('topics_discussed')}
            onBlur={refreshSuggestions}
          />
        </div>

        <div className="materials-block">
          <div className="materials-title">Materials Shared / Samples Distributed</div>
          <ListEditor
            label="Materials Shared"
            field="materials_shared"
            placeholder="e.g. OncoBoost brochure"
            buttonLabel="Search/Add"
          />
          <ListEditor
            label="Samples Distributed"
            field="samples_distributed"
            placeholder="e.g. 2 starter kits"
            buttonLabel="Add Sample"
          />
        </div>

        <div className="field">
          <label>Observed/Inferred HCP Sentiment</label>
          <div className="sentiment-row">
            {SENTIMENTS.map((s) => (
              <label
                key={s.value}
                className={`sentiment-option ${form.sentiment === s.value ? 'active' : ''}`}
              >
                <input
                  type="radio"
                  name="sentiment"
                  value={s.value}
                  checked={form.sentiment === s.value}
                  onChange={onChange('sentiment')}
                />
                <span className="sentiment-emoji" style={{ color: s.color }}>
                  {s.emoji}
                </span>
                <span>{s.value}</span>
              </label>
            ))}
          </div>
        </div>

        <div className="field">
          <label>Outcomes</label>
          <textarea
            className="textarea"
            placeholder="Key outcomes or agreements..."
            value={form.outcomes || ''}
            onChange={onChange('outcomes')}
            onBlur={refreshSuggestions}
          />
        </div>

        <div className="field">
          <label>Follow-up Actions</label>
          <textarea
            className="textarea"
            placeholder="Enter next steps or tasks..."
            value={form.follow_up_actions || ''}
            onChange={onChange('follow_up_actions')}
          />
        </div>

        <div className="ai-suggestions">
          <div className="ai-suggestions-label">AI Suggested Follow-ups:</div>
          <ul>
            {suggestions.map((s) => (
              <li key={s}>
                <button
                  type="button"
                  className="suggestion-link"
                  onClick={() => dispatch(appendFollowUp(s))}
                >
                  + {s}
                </button>
              </li>
            ))}
          </ul>
        </div>

        {form.summary && (
          <div className="summary-box">
            <div className="summary-label">AI Summary</div>
            <p>{form.summary}</p>
          </div>
        )}
      </div>

      {/* Pinned footer — always visible while form body scrolls */}
      <div className="form-actions">
        <button type="button" className="btn btn-secondary" onClick={() => dispatch(resetForm())}>
          Reset
        </button>
        <button
          type="button"
          className="btn btn-primary"
          onClick={onSave}
          disabled={status === 'saving'}
        >
          {status === 'saving' && <span className="spinner" />}
          {currentInteractionId ? 'Update Interaction' : 'Save Interaction'}
        </button>
      </div>
    </div>
  )
}
