import { Menu, LogOut, User } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../store/useAuthStore'

interface TopBarProps {
  onMenuClick: () => void
}

export default function TopBar({ onMenuClick }: TopBarProps) {
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()

  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <header className="md:hidden flex items-center justify-between h-14 px-4 bg-slate-900 border-b border-slate-700/50 flex-shrink-0">
      <button
        onClick={onMenuClick}
        className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
        aria-label="Open menu"
      >
        <Menu className="w-5 h-5" />
      </button>

      <span className="font-semibold text-white text-sm">Contact Forecasting</span>

      <div className="flex items-center gap-2">
        {user && (
          <span className="text-xs text-slate-400 hidden sm:block">{user.username}</span>
        )}
        <button
          onClick={handleLogout}
          className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
          aria-label="Logout"
        >
          <LogOut className="w-4 h-4" />
        </button>
      </div>
    </header>
  )
}
