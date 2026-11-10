import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { useAuth } from './auth'
import { Spinner } from './ui'
import Layout from './components/Layout'
import Login from './pages/Login'
import SsoCallback from './pages/SsoCallback'
import Dashboard from './pages/Dashboard'
import Chat from './pages/Chat'
import Regulations from './pages/Regulations'
import Rules from './pages/Rules'
import Advisor from './pages/Advisor'
import Processes from './pages/Processes'
import Deadlines from './pages/Deadlines'
import Tickets from './pages/Tickets'
import Admin from './pages/Admin'

function RequireAuth({ children }) {
  const { user, loading } = useAuth()
  const loc = useLocation()
  if (loading) return <div className="min-h-screen flex items-center justify-center"><Spinner label="در حال بررسی نشست…" /></div>
  if (!user) return <Navigate to="/login" state={{ from: loc }} replace />
  return children
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/sso/callback" element={<SsoCallback />} />
      <Route element={<RequireAuth><Layout /></RequireAuth>}>
        <Route index element={<Dashboard />} />
        <Route path="chat" element={<Chat />} />
        <Route path="regulations" element={<Regulations />} />
        <Route path="rules" element={<Rules />} />
        <Route path="advisor" element={<Advisor />} />
        <Route path="processes" element={<Processes />} />
        <Route path="deadlines" element={<Deadlines />} />
        <Route path="tickets" element={<Tickets />} />
        <Route path="admin" element={<Admin />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
