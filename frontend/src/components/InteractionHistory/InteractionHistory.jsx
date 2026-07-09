import { useSelector } from 'react-redux'
import './InteractionHistory.css'

export default function InteractionHistory() {
  const { history, form } = useSelector((s) => s.interaction)

  if (!form.hcp_id) return null

  return (
    <div className="history-panel card">
      <div className="card-header">
        Prior Interactions
        {form.hcp_name ? ` — ${form.hcp_name}` : ''}
      </div>
      <div className="card-body history-body">
        {history.length === 0 && (
          <p className="history-empty">No previous interactions logged for this HCP.</p>
        )}
        <ul className="history-list">
          {history.map((row) => (
            <li key={row.id} className="history-item">
              <div className="history-top">
                <span className="history-type">{row.interaction_type}</span>
                <span className="history-date">{row.interaction_date}</span>
                <span className={`badge badge-${(row.sentiment || 'neutral').toLowerCase()}`}>
                  {row.sentiment || 'Neutral'}
                </span>
              </div>
              {(row.summary || row.topics_discussed) && (
                <p className="history-summary">{row.summary || row.topics_discussed}</p>
              )}
              {row.outcomes && <p className="history-outcomes">Outcomes: {row.outcomes}</p>}
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
