import { Moon, Sun } from 'lucide-react'
import { useAppStore } from '../../store/useAppStore'

export default function ThemeToggle() {
  const { theme, toggleTheme } = useAppStore()
  return (
    <button
      onClick={toggleTheme}
      className="p-2 rounded-lg hover:bg-white/10 transition-colors"
      title={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
    >
      {theme === 'light' ? (
        <Moon className="w-5 h-5 text-slate-400" />
      ) : (
        <Sun className="w-5 h-5 text-yellow-300" />
      )}
    </button>
  )
}
