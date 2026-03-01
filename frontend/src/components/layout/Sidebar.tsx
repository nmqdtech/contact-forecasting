import { Activity, BarChart3, Download, Home, LineChart, Settings } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import ThemeToggle from './ThemeToggle'

const navItems = [
  { to: '/dashboard', icon: Home, label: 'Dashboard' },
  { to: '/forecasts', icon: LineChart, label: 'Forecasts' },
  { to: '/analysis', icon: BarChart3, label: 'Analysis' },
  { to: '/settings', icon: Settings, label: 'Settings' },
  { to: '/export', icon: Download, label: 'Export' },
]

export default function Sidebar() {
  return (
    <aside className="flex flex-col w-60 min-h-screen bg-slate-900 border-r border-slate-700/50 flex-shrink-0">
      {/* Brand */}
      <div className="flex items-center gap-3 px-5 py-5 border-b border-white/10">
        <Activity className="w-7 h-7 text-blue-400 flex-shrink-0" />
        <div>
          <p className="font-semibold text-white text-sm leading-tight">Contact</p>
          <p className="text-xs text-slate-400 leading-tight">Forecasting</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 px-3 space-y-0.5">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-400 hover:bg-white/10 hover:text-white'
              }`
            }
          >
            <Icon className="w-4 h-4 flex-shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-4 py-4 border-t border-white/10 flex justify-between items-center">
        <span className="text-xs text-slate-500">v1.0</span>
        <ThemeToggle />
      </div>
    </aside>
  )
}
