import { useEffect, useRef, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { fetchHcps, selectHcp, loadHcpHistory, loadSuggestions } from '../../store/slices/interactionSlice'
import './HCPSearch.css'

export default function HCPSearch() {
  const dispatch = useDispatch()
  const { form, hcps, hcpSearchLoading } = useSelector((s) => s.interaction)
  const [query, setQuery] = useState(form.hcp_name || '')
  const [open, setOpen] = useState(false)
  const wrapRef = useRef(null)
  const timer = useRef(null)

  useEffect(() => {
    setQuery(form.hcp_name || '')
  }, [form.hcp_name])

  useEffect(() => {
    const onDoc = (e) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [])

  const onChange = (e) => {
    const v = e.target.value
    setQuery(v)
    setOpen(true)
    clearTimeout(timer.current)
    timer.current = setTimeout(() => {
      dispatch(fetchHcps(v.trim() || undefined))
    }, 220)
  }

  const onFocus = () => {
    setOpen(true)
    if (!hcps.length) dispatch(fetchHcps())
  }

  const pick = (hcp) => {
    dispatch(selectHcp(hcp))
    dispatch(loadHcpHistory(hcp.id))
    dispatch(
      loadSuggestions({
        hcp_name: hcp.name,
        specialty: hcp.specialty,
        topics_discussed: form.topics_discussed,
        outcomes: form.outcomes,
      })
    )
    setQuery(hcp.name)
    setOpen(false)
  }

  return (
    <div className="field hcp-search" ref={wrapRef}>
      <label>HCP Name</label>
      <div className="hcp-input-wrap">
        <input
          className="input"
          placeholder="Search or select HCP..."
          value={query}
          onChange={onChange}
          onFocus={onFocus}
          autoComplete="off"
        />
        {hcpSearchLoading && <span className="hcp-spinner spinner dark" />}
      </div>
      {open && (
        <div className="hcp-dropdown">
          {hcps.length === 0 && !hcpSearchLoading && (
            <div className="hcp-empty">No HCPs found</div>
          )}
          {hcps.map((h) => (
            <button
              type="button"
              key={h.id}
              className={`hcp-option ${form.hcp_id === h.id ? 'selected' : ''}`}
              onClick={() => pick(h)}
            >
              <div className="hcp-option-name">{h.name}</div>
              <div className="hcp-option-meta">
                {[h.specialty, h.hospital, h.location].filter(Boolean).join(' · ')}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
