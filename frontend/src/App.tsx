import { useEffect } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import AppShell from './components/layout/AppShell'
import ProtectedRoute from './components/layout/ProtectedRoute'
import Analysis from './pages/Analysis'
import ChangePassword from './pages/ChangePassword'
import Dashboard from './pages/Dashboard'
import Export from './pages/Export'
import Forecasts from './pages/Forecasts'
import Login from './pages/Login'
import Settings from './pages/Settings'
import { useAppStore } from './store/useAppStore'

export default function App() {
  const theme = useAppStore((s) => s.theme)

  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [theme])

  return (
    <Routes>
      {/* Public */}
      <Route path="/login" element={<Login />} />

      {/* Change password — requires token, accessible even when must_change_password=true */}
      <Route
        path="/change-password"
        element={
          <ProtectedRoute>
            <ChangePassword />
          </ProtectedRoute>
        }
      />

      {/* Protected — wrapped in AppShell */}
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <AppShell>
              <Routes>
                <Route path="/" element={<Navigate to="/dashboard" replace />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/forecasts" element={<Forecasts />} />
                <Route path="/analysis" element={<Analysis />} />
                <Route path="/settings" element={<Settings />} />
                <Route path="/export" element={<Export />} />
                <Route path="/admin" element={<Navigate to="/settings" replace />} />
              </Routes>
            </AppShell>
          </ProtectedRoute>
        }
      />
    </Routes>
  )
}
