import { Activity, BarChart3, Download, Home, LineChart, LogOut, Settings, Shield, X } from 'lucide-react'
import { NavLink, useNavigate } from 'react-router-dom'
import ThemeToggle from './ThemeToggle'
import { useAuthStore } from '../../store/useAuthStore'

const navItems = [
  { to: '/dashboard', icon: Home, label: 'Dashboard' },
  { to: '/forecasts', icon: LineChart, label: 'Forecasts' },
  { to: '/analysis', icon: BarChart3, label: 'Analysis' },
  { to: '/settings', icon: Settings, label: 'Settings' },
  { to: '/export', icon: Download, label: 'Export' },
]

interface SidebarProps {
  open?: boolean
  onClose?: () => void
}

export default function Sidebar({ open, onClose }: SidebarProps) {
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()

  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <>
      {/* Mobile overlay backdrop */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={`
          fixed inset-y-0 left-0 z-50 flex flex-col w-60 min-h-screen bg-slate-900 border-r border-slate-700/50 flex-shrink-0
          transition-transform duration-200
          md:relative md:translate-x-0
          ${open ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
        `}
      >
        {/* Brand + mobile close */}
        <div className="flex items-center gap-3 px-5 py-5 border-b border-white/10">
          <Activity className="w-7 h-7 text-blue-400 flex-shrink-0" />
          <div className="flex-1">
            <p className="font-semibold text-white text-sm leading-tight">Contact</p>
            <p className="text-xs text-slate-400 leading-tight">Forecasting</p>
          </div>
          {/* Close button — mobile only */}
          <button
            onClick={onClose}
            className="md:hidden p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-4 px-3 space-y-0.5">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              onClick={onClose}
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

          {user?.is_admin && (
            <NavLink
              to="/admin"
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-blue-600 text-white'
                    : 'text-slate-400 hover:bg-white/10 hover:text-white'
                }`
              }
            >
              <Shield className="w-4 h-4 flex-shrink-0" />
              Admin
            </NavLink>
          )}
        </nav>

        {/* Footer: user info + logout */}
        <div className="px-4 py-4 border-t border-white/10 space-y-2">
          {user && (
            <div className="flex items-center gap-2 px-1">
              <div className="w-7 h-7 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0">
                <span className="text-xs font-bold text-white">
                  {user.username[0].toUpperCase()}
                </span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-white truncate">{user.username}</p>
                {user.is_admin && (
                  <p className="text-xs text-amber-400 leading-tight">Admin</p>
                )}
              </div>
              <button
                onClick={handleLogout}
                title="Logout"
                className="p-1.5 rounded-lg text-slate-500 hover:text-white hover:bg-white/10 transition-colors flex-shrink-0"
              >
                <LogOut className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
          <div className="flex justify-between items-center px-1">
            <span className="text-xs text-slate-500">v1.0</span>
            <ThemeToggle />
          </div>
        </div>
      </aside>
    </>
  )
}
