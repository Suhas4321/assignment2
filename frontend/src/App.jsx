import Sidebar from './components/Sidebar/Sidebar'
import LogInteraction from './pages/LogInteraction'

export default function App() {
  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-content">
        <LogInteraction />
      </main>
    </div>
  )
}
