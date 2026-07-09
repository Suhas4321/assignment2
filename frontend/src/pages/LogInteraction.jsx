import { useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import LogInteractionForm from '../components/LogInteractionForm/LogInteractionForm'
import ChatInterface from '../components/ChatInterface/ChatInterface'
import { clearToast, fetchHcps } from '../store/slices/interactionSlice'
import './LogInteraction.css'

export default function LogInteraction() {
  const dispatch = useDispatch()
  const toast = useSelector((s) => s.interaction.toast)

  useEffect(() => {
    dispatch(fetchHcps())
  }, [dispatch])

  useEffect(() => {
    if (!toast) return
    const t = setTimeout(() => dispatch(clearToast()), 3500)
    return () => clearTimeout(t)
  }, [toast, dispatch])

  return (
    <div className="log-page">
      <header className="log-page-header">
        <h1 className="page-title">Log HCP Interaction</h1>
        <p className="page-subtitle">
          Use the structured form on the left, or describe the visit to the AI Assistant on the right —
          fields populate automatically.
        </p>
      </header>

      <div className="log-layout">
        {/* LEFT — structured form (assignment mockup) */}
        <section className="log-main" aria-label="Interaction form">
          <LogInteractionForm />
        </section>

        {/* RIGHT — AI chat (assignment mockup) */}
        <aside className="log-side" aria-label="AI Assistant">
          <ChatInterface />
        </aside>
      </div>

      {toast && (
        <div className={`toast ${toast.type || ''}`} role="status">
          {toast.message}
        </div>
      )}
    </div>
  )
}
