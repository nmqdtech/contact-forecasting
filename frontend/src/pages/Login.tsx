import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Activity } from 'lucide-react'
import { login, verifyTotp, getMe } from '../api/auth'
import { useAuthStore } from '../store/useAuthStore'

export default function Login() {
  const navigate = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [totpCode, setTotpCode] = useState('')
  const [tempToken, setTempToken] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await login(username, password)
      if ('requires_2fa' in res && res.requires_2fa) {
        setTempToken(res.temp_token)
      } else {
        const { access_token } = res
        localStorage.setItem(
          'forecasting-auth',
          JSON.stringify({ state: { token: access_token, user: null } })
        )
        const user = await getMe()
        setAuth(access_token, user)
        navigate('/dashboard', { replace: true })
      }
    } catch {
      setError('Invalid username or password')
    } finally {
      setLoading(false)
    }
  }

  async function handleTotpSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!tempToken) return
    setError('')
    setLoading(true)
    try {
      const { access_token } = await verifyTotp(tempToken, totpCode)
      localStorage.setItem(
        'forecasting-auth',
        JSON.stringify({ state: { token: access_token, user: null } })
      )
      const user = await getMe()
      setAuth(access_token, user)
      navigate('/dashboard', { replace: true })
    } catch {
      setError('Invalid authenticator code')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950">
      <div className="w-full max-w-sm">
        {/* Brand */}
        <div className="flex items-center justify-center gap-3 mb-8">
          <Activity className="w-8 h-8 text-blue-400" />
          <div className="text-left">
            <p className="font-bold text-white text-lg leading-tight">Contact</p>
            <p className="text-sm text-slate-400 leading-tight">Forecasting</p>
          </div>
        </div>

        {tempToken ? (
          /* ── Step 2: TOTP code ── */
          <form
            onSubmit={handleTotpSubmit}
            className="bg-slate-900 border border-slate-700/50 rounded-2xl p-8 space-y-5"
          >
            <h1 className="text-xl font-semibold text-white text-center">Two-Factor Auth</h1>
            <p className="text-sm text-slate-400 text-center">
              Enter the 6-digit code from your authenticator app.
            </p>

            {error && (
              <div className="bg-red-900/30 border border-red-700/50 text-red-300 text-sm px-4 py-2.5 rounded-lg">
                {error}
              </div>
            )}

            <div className="space-y-1">
              <label className="block text-sm text-slate-400">Authenticator code</label>
              <input
                type="text"
                inputMode="numeric"
                pattern="[0-9]{6}"
                maxLength={6}
                autoFocus
                required
                value={totpCode}
                onChange={(e) => setTotpCode(e.target.value)}
                placeholder="000000"
                className="w-full bg-slate-800 border border-slate-600 text-white rounded-lg px-3 py-2.5 text-sm text-center tracking-widest focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <button
              type="submit"
              disabled={loading || totpCode.length !== 6}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white font-medium py-2.5 rounded-lg text-sm transition-colors"
            >
              {loading ? 'Verifying…' : 'Verify'}
            </button>

            <button
              type="button"
              onClick={() => { setTempToken(null); setError('') }}
              className="w-full text-sm text-slate-500 hover:text-slate-300 transition-colors"
            >
              ← Back to sign in
            </button>
          </form>
        ) : (
          /* ── Step 1: Username + password ── */
          <form
            onSubmit={handleSubmit}
            className="bg-slate-900 border border-slate-700/50 rounded-2xl p-8 space-y-5"
          >
            <h1 className="text-xl font-semibold text-white text-center">Sign in</h1>

            {error && (
              <div className="bg-red-900/30 border border-red-700/50 text-red-300 text-sm px-4 py-2.5 rounded-lg">
                {error}
              </div>
            )}

            <div className="space-y-1">
              <label className="block text-sm text-slate-400">Username</label>
              <input
                type="text"
                autoFocus
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full bg-slate-800 border border-slate-600 text-white rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="space-y-1">
              <label className="block text-sm text-slate-400">Password</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-slate-800 border border-slate-600 text-white rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white font-medium py-2.5 rounded-lg text-sm transition-colors"
            >
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
