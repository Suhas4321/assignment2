import './Sidebar.css'

const icons = {
  home: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M3 10.5 12 3l9 7.5V21a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1v-10.5z" />
    </svg>
  ),
  log: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" />
      <rect x="9" y="3" width="6" height="4" rx="1" />
      <path d="M9 12h6M9 16h4" />
    </svg>
  ),
  users: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <circle cx="9" cy="8" r="3.5" />
      <path d="M2.5 19c0-3 2.9-5.5 6.5-5.5s6.5 2.5 6.5 5.5" />
      <circle cx="17" cy="9" r="2.5" />
      <path d="M21.5 19c0-2.2-1.8-4-4.2-4.5" />
    </svg>
  ),
  calendar: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <rect x="3" y="5" width="18" height="16" rx="2" />
      <path d="M3 10h18M8 3v4M16 3v4" />
    </svg>
  ),
  spark: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M12 3l1.5 5.5L19 10l-5.5 1.5L12 17l-1.5-5.5L5 10l5.5-1.5L12 3z" />
    </svg>
  ),
}

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-logo" title="AI CRM">
        <span className="logo-mark">AI</span>
      </div>
      <nav className="sidebar-nav">
        <button className="nav-item" title="Home" type="button">
          {icons.home}
        </button>
        <button className="nav-item active" title="Log Interaction" type="button">
          {icons.log}
        </button>
        <button className="nav-item" title="HCPs" type="button">
          {icons.users}
        </button>
        <button className="nav-item" title="Follow-ups" type="button">
          {icons.calendar}
        </button>
        <button className="nav-item" title="AI Agent" type="button">
          {icons.spark}
        </button>
      </nav>
      <div className="sidebar-footer">
        <div className="rep-avatar" title="REP-001">R</div>
      </div>
    </aside>
  )
}
