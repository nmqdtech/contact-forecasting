import { useEffect } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import AppShell from './components/layout/AppShell'
import Analysis from './pages/Analysis'
import Dashboard from './pages/Dashboard'
import Export from './pages/Export'
import Forecasts from './pages/Forecasts'
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
    <AppShell>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/forecasts" element={<Forecasts />} />
        <Route path="/analysis" element={<Analysis />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/export" element={<Export />} />
      </Routes>
    </AppShell>
  )
}
