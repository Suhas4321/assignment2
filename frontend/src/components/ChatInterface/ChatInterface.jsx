import { useEffect, useRef, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { sendChatMessage, resetChat } from '../../store/slices/chatSlice'
import './ChatInterface.css'

export default function ChatInterface() {
  const dispatch = useDispatch()
  const { messages, status, toolsUsed } = useSelector((s) => s.chat)
  const { form } = useSelector((s) => s.interaction)
  const [text, setText] = useState('')
  const bottomRef = useRef(null)
  const bodyRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    const body = bodyRef.current
    if (!body) return
    body.scrollTop = body.scrollHeight
  }, [messages, status])

  // Grow textarea so pasted multi-line notes stay fully visible
  useEffect(() => {
    const el = inputRef.current
    if (!el) return
    el.style.height = 'auto'
    const max = 160 // ~6–7 lines
    el.style.height = `${Math.min(el.scrollHeight, max)}px`
  }, [text])

  const send = () => {
    const m = text.trim()
    if (!m || status === 'streaming') return
    setText('')
    dispatch(
      sendChatMessage({
        message: m,
        hcpId: form.hcp_id,
        repId: form.rep_id,
      })
    )
  }

  const onKey = (e) => {
    // Enter = send, Shift+Enter = new line
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <div className="card chat-card">
      <div className="card-header chat-header">
        <div className="chat-title">
          <span className="ai-orb" aria-hidden />
          <div>
            <div className="chat-title-text">AI Assistant</div>
            <div className="chat-subtitle">Log interaction details here via chat</div>
          </div>
        </div>
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          onClick={() => dispatch(resetChat())}
          title="Reset conversation"
        >
          Reset
        </button>
      </div>

      <div className="chat-body" ref={bodyRef}>
        {messages.map((m) => (
          <div
            key={m.id}
            className={[
              'chat-bubble',
              m.role === 'user' ? 'user' : 'assistant',
              m.isError ? 'error' : '',
              m.isSuccess ? 'success' : '',
            ]
              .filter(Boolean)
              .join(' ')}
          >
            <div className="bubble-content">{m.content}</div>
            {m.tools?.length > 0 && (
              <div className="bubble-tools">
                {m.tools.map((t) => (
                  <span key={t} className="tool-chip">
                    ⚙ {t}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
        {status === 'streaming' && (
          <div className="chat-bubble assistant">
            <div className="typing">
              <span />
              <span />
              <span />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {toolsUsed.length > 0 && (
        <div className="tools-bar">
          <span className="tools-label">Tools used:</span>
          {toolsUsed.map((t) => (
            <span key={t} className="tool-chip">
              {t}
            </span>
          ))}
        </div>
      )}

      <div className="chat-input-row">
        <textarea
          ref={inputRef}
          className="input chat-input chat-textarea"
          placeholder="Describe interaction… (Shift+Enter for new line)"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKey}
          disabled={status === 'streaming'}
          rows={4}
        />
        <button
          type="button"
          className="btn btn-primary chat-send"
          onClick={send}
          disabled={status === 'streaming' || !text.trim()}
        >
          {status === 'streaming' ? (
            <span className="spinner" />
          ) : (
            <>
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.2"
              >
                <path d="M12 19V5M5 12l7-7 7 7" />
              </svg>
              Log
            </>
          )}
        </button>
      </div>
    </div>
  )
}
