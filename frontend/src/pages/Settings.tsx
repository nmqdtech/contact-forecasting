import { useEffect, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ShieldCheck, ShieldOff, Trash2, UserCheck, UserPlus, UserX, Users } from 'lucide-react'
import { QRCodeSVG } from 'qrcode.react'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import { useChannels } from '../hooks/useChannels'
import { useConfig, useDeleteHoliday, useDeleteTargets, useSetHoliday, useSetTargets } from '../hooks/useConfig'
import { setupTotp, enableTotp, disableTotp, listUsers, createUser, updateUser, deleteUser, type TotpSetupResponse, type UserOut } from '../api/auth'
import { useAuthStore } from '../store/useAuthStore'
import { listHiringWaves, createHiringWave, deleteHiringWave } from '../api/hiringWaves'
import type { HiringWave } from '../types'

const COUNTRIES: Record<string, string> = {
  GB: 'United Kingdom', US: 'United States', FR: 'France', DE: 'Germany',
  ES: 'Spain', IT: 'Italy', NL: 'Netherlands', BE: 'Belgium', MA: 'Morocco',
  CA: 'Canada', AU: 'Australia', PT: 'Portugal', IE: 'Ireland',
  SE: 'Sweden', NO: 'Norway', DK: 'Denmark', CH: 'Switzerland',
  AE: 'United Arab Emirates', SA: 'Saudi Arabia', ZA: 'South Africa',
}

const MONTH_NAMES = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

export default function Settings() {
  const { data: channels } = useChannels()
  const { data: config } = useConfig()
  const currentUser = useAuthStore((s) => s.user)
  const qc = useQueryClient()

  // ── User management state (admin only) ───────────────────────────────────────
  const { data: users = [] } = useQuery<UserOut[]>({
    queryKey: ['users'],
    queryFn: listUsers,
    enabled: !!currentUser?.is_admin,
  })
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ username: '', email: '', password: '', is_admin: false })
  const [formError, setFormError] = useState('')

  const createMut = useMutation({
    mutationFn: createUser,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] })
      setForm({ username: '', email: '', password: '', is_admin: false })
      setShowForm(false)
      setFormError('')
    },
    onError: (err: any) => setFormError(err?.response?.data?.detail || 'Failed to create user'),
  })

  const updateMut = useMutation({
    mutationFn: ({ id, body }: { id: string; body: { is_active?: boolean; is_admin?: boolean } }) =>
      updateUser(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  })

  const deleteMut = useMutation({
    mutationFn: deleteUser,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  })

  // ── Holiday state ─────────────────────────────────────────────────────────────
  const [holChannel, setHolChannel] = useState('')
  const [holCountry, setHolCountry] = useState('GB')
  const setHoliday = useSetHoliday()
  const deleteHoliday = useDeleteHoliday()

  // ── Targets state ─────────────────────────────────────────────────────────────
  const currentYear = new Date().getFullYear()
  const [tgtChannel, setTgtChannel] = useState('')
  const [tgtYear, setTgtYear] = useState(currentYear)
  const [tgtValues, setTgtValues] = useState<Record<string, string>>({})
  const setTargets = useSetTargets()
  const deleteTargets = useDeleteTargets()

  useEffect(() => {
    if (!tgtChannel || !config) { setTgtValues({}); return }
    const channelTargets = (config.targets[tgtChannel] ?? {}) as Record<string, number>
    const populated: Record<string, string> = {}
    for (const [month, vol] of Object.entries(channelTargets)) {
      if (month.startsWith(`${tgtYear}-`)) populated[month] = String(vol)
    }
    setTgtValues(populated)
  }, [tgtChannel, tgtYear, config])

  const channelNames = channels?.map((c) => c.name) ?? []

  // ── Hiring Waves state ────────────────────────────────────────────────────────
  const [waveChannel, setWaveChannel] = useState('')
  const [waveForm, setWaveForm] = useState({
    label: '',
    start_date: '',
    end_date: '',
    junior_count: '',
    total_agents: '',
  })
  const [waveError, setWaveError] = useState('')

  const { data: allWaves = [] } = useQuery<HiringWave[]>({
    queryKey: ['hiring-waves'],
    queryFn: () => listHiringWaves(),
  })

  const createWaveMut = useMutation({
    mutationFn: createHiringWave,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['hiring-waves'] })
      setWaveForm({ label: '', start_date: '', end_date: '', junior_count: '', total_agents: '' })
      setWaveError('')
    },
    onError: (err: any) => setWaveError(err?.response?.data?.detail || 'Failed to create hiring wave'),
  })

  const deleteWaveMut = useMutation({
    mutationFn: deleteHiringWave,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['hiring-waves'] }),
  })

  function handleCreateWave() {
    if (!waveChannel || !waveForm.start_date || !waveForm.end_date || !waveForm.junior_count || !waveForm.total_agents) {
      setWaveError('All fields except Label are required')
      return
    }
    const junior_count = parseInt(waveForm.junior_count, 10)
    const total_agents = parseInt(waveForm.total_agents, 10)
    if (isNaN(junior_count) || isNaN(total_agents) || junior_count < 0 || total_agents <= 0) {
      setWaveError('Junior count and total agents must be positive numbers')
      return
    }
    if (junior_count > total_agents) {
      setWaveError('Junior count cannot exceed total agents')
      return
    }
    setWaveError('')
    createWaveMut.mutate({
      channel: waveChannel,
      start_date: waveForm.start_date,
      end_date: waveForm.end_date,
      junior_count,
      total_agents,
      label: waveForm.label || undefined,
    })
  }

  const wavesForChannel = waveChannel ? allWaves.filter((w) => w.channel === waveChannel) : []
  const waveJuniorRatio =
    waveForm.junior_count && waveForm.total_agents
      ? (parseInt(waveForm.junior_count, 10) / parseInt(waveForm.total_agents, 10))
      : null

  // ── 2FA state ─────────────────────────────────────────────────────────────────
  const setTotpEnabled = useAuthStore((s) => s.setTotpEnabled)
  const [totpSetup, setTotpSetup] = useState<TotpSetupResponse | null>(null)
  const [totpCode, setTotpCode] = useState('')
  const [totpLoading, setTotpLoading] = useState(false)
  const [totpError, setTotpError] = useState('')

  const handleSetupTotp = async () => {
    setTotpLoading(true); setTotpError('')
    try { const data = await setupTotp(); setTotpSetup(data); setTotpCode('') }
    catch { setTotpError('Failed to set up 2FA') }
    finally { setTotpLoading(false) }
  }

  const handleEnableTotp = async () => {
    setTotpLoading(true); setTotpError('')
    try { await enableTotp(totpCode); setTotpEnabled(true); setTotpSetup(null); setTotpCode('') }
    catch { setTotpError('Invalid code — try again') }
    finally { setTotpLoading(false) }
  }

  const handleDisableTotp = async () => {
    setTotpLoading(true); setTotpError('')
    try { await disableTotp(); setTotpEnabled(false) }
    catch { setTotpError('Failed to disable 2FA') }
    finally { setTotpLoading(false) }
  }

  const handleSetHoliday = () => {
    if (!holChannel) return
    setHoliday.mutate({ channel: holChannel, country_code: holCountry })
  }

  const handleSaveTargets = () => {
    if (!tgtChannel) return
    const targets: Record<string, number> = {}
    for (const [month, vol] of Object.entries(tgtValues)) {
      const n = Number(vol)
      if (vol !== '' && !isNaN(n) && n > 0) targets[month] = n
    }
    if (Object.keys(targets).length === 0) return
    setTargets.mutate({ channel: tgtChannel, targets })
  }

  const inputCls =
    'block w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'

  const yearOptions = [currentYear - 1, currentYear, currentYear + 1]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Settings</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Manage users, security, bank holidays, and monthly volume targets
        </p>
      </div>

      {/* ── User Management & Security ────────────────────────────────────────── */}
      <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200">
              {currentUser?.is_admin ? 'User Management & Security' : 'Account Security'}
            </h2>
          {currentUser?.is_admin && (
            <button
              onClick={() => setShowForm((v) => !v)}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded-lg text-sm font-medium transition-colors"
            >
              <UserPlus className="w-4 h-4" />
              Add User
            </button>
          )}
          </div>

          {/* Admin only: create form + user table */}
          {currentUser?.is_admin && (
            <>
              {/* Create user form */}
              {showForm && (
                <div className="mb-5 rounded-xl border border-slate-200 dark:border-slate-700 p-4 space-y-4">
                  <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">New User</h3>
                  {formError && <p className="text-sm text-red-500">{formError}</p>}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs text-slate-500 dark:text-slate-400 mb-1">Username</label>
                      <input value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} className={inputCls} />
                    </div>
                    <div>
                      <label className="block text-xs text-slate-500 dark:text-slate-400 mb-1">Email</label>
                      <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className={inputCls} />
                    </div>
                    <div>
                      <label className="block text-xs text-slate-500 dark:text-slate-400 mb-1">Password</label>
                      <input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} className={inputCls} />
                    </div>
                    <div className="flex items-end pb-1">
                      <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300 cursor-pointer">
                        <input type="checkbox" checked={form.is_admin} onChange={(e) => setForm({ ...form, is_admin: e.target.checked })} className="rounded" />
                        Admin
                      </label>
                    </div>
                  </div>
                  <div className="flex gap-3">
                    <button onClick={() => createMut.mutate(form)} disabled={createMut.isPending}
                      className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-60">
                      {createMut.isPending ? 'Creating…' : 'Create User'}
                    </button>
                    <button onClick={() => { setShowForm(false); setFormError('') }}
                      className="text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 px-4 py-2 rounded-lg text-sm">
                      Cancel
                    </button>
                  </div>
                </div>
              )}

              {/* User table */}
              <div className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50 dark:bg-slate-900/50 text-slate-500 dark:text-slate-400 text-xs uppercase tracking-wide">
                    <tr>
                      <th className="px-4 py-3 text-left">Username</th>
                      <th className="px-4 py-3 text-left hidden sm:table-cell">Email</th>
                      <th className="px-4 py-3 text-left">Role</th>
                      <th className="px-4 py-3 text-left">Status</th>
                      <th className="px-4 py-3 text-left">2FA</th>
                      <th className="px-4 py-3 text-left">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
                    {users.map((u: UserOut) => (
                      <tr key={u.id} className="hover:bg-slate-50 dark:hover:bg-slate-700/30">
                        <td className="px-4 py-3 font-medium text-slate-900 dark:text-white">
                          {u.username}
                          {u.id === currentUser.id && <span className="ml-1.5 text-xs text-blue-500">(you)</span>}
                        </td>
                        <td className="px-4 py-3 text-slate-500 dark:text-slate-400 hidden sm:table-cell">{u.email}</td>
                        <td className="px-4 py-3">
                          {u.is_admin ? (
                            <span className="inline-flex items-center gap-1 text-amber-600 dark:text-amber-400 text-xs font-medium">
                              <ShieldCheck className="w-3.5 h-3.5" /> Admin
                            </span>
                          ) : (
                            <span className="text-slate-400 text-xs">User</span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`text-xs font-medium ${u.is_active ? 'text-green-600 dark:text-green-400' : 'text-red-500'}`}>
                            {u.is_active ? 'Active' : 'Disabled'}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          {u.totp_enabled ? (
                            <span className="text-xs font-medium text-emerald-600 dark:text-emerald-400">✓ On</span>
                          ) : (
                            <span className="text-xs text-slate-400">—</span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          {u.id !== currentUser.id && (
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => updateMut.mutate({ id: u.id, body: { is_active: !u.is_active } })}
                                title={u.is_active ? 'Disable user' : 'Enable user'}
                                className="text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition-colors"
                              >
                                {u.is_active ? <UserX className="w-4 h-4" /> : <UserCheck className="w-4 h-4" />}
                              </button>
                              <button
                                onClick={() => updateMut.mutate({ id: u.id, body: { is_admin: !u.is_admin } })}
                                title={u.is_admin ? 'Remove admin' : 'Make admin'}
                                className="text-slate-400 hover:text-amber-500 transition-colors"
                              >
                                {u.is_admin ? <ShieldOff className="w-4 h-4" /> : <ShieldCheck className="w-4 h-4" />}
                              </button>
                              <button
                                onClick={() => { if (confirm(`Delete user "${u.username}"? This cannot be undone.`)) deleteMut.mutate(u.id) }}
                                title="Delete user"
                                className="text-slate-400 hover:text-red-500 transition-colors"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}

          {/* ── Two-Factor Authentication — all users ─────────────────────────── */}
          <div className="mt-6 border-t border-slate-200 dark:border-slate-700 pt-5">
            <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200 mb-1">
              Two-Factor Authentication
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
              Add an extra layer of security using an authenticator app (Google Authenticator, Authy).
            </p>

            {totpError && (
              <div className="mb-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-sm px-3 py-2 rounded-lg">
                {totpError}
              </div>
            )}

            {currentUser?.totp_enabled ? (
              <div className="flex items-center gap-4">
                <span className="text-sm text-emerald-600 dark:text-emerald-400 font-medium">✓ 2FA is enabled</span>
                <Button variant="secondary" loading={totpLoading} onClick={handleDisableTotp}>Disable 2FA</Button>
              </div>
            ) : totpSetup ? (
              <div className="space-y-4">
                <p className="text-sm text-slate-600 dark:text-slate-400">
                  Scan this QR code with your authenticator app, then enter the 6-digit code to confirm.
                </p>
                <div className="flex flex-wrap gap-6 items-start">
                  <div className="bg-white p-3 rounded-lg inline-block">
                    <QRCodeSVG value={totpSetup.otpauth_url} size={160} />
                  </div>
                  <div className="flex-1 min-w-48 space-y-3">
                    <div>
                      <p className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-1">Manual entry key</p>
                      <code className="text-xs bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded break-all">{totpSetup.secret}</code>
                    </div>
                    <div className="space-y-2">
                      <input
                        type="text" inputMode="numeric" pattern="[0-9]{6}" maxLength={6}
                        placeholder="6-digit code" value={totpCode}
                        onChange={(e) => setTotpCode(e.target.value)} className={inputCls}
                      />
                      <div className="flex gap-2">
                        <Button onClick={handleEnableTotp} loading={totpLoading} disabled={totpCode.length !== 6}>
                          Verify & Enable
                        </Button>
                        <Button variant="secondary" onClick={() => { setTotpSetup(null); setTotpError('') }}>
                          Cancel
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <Button loading={totpLoading} onClick={handleSetupTotp}>Set up 2FA</Button>
            )}
          </div>
        </Card>

      {/* ── Bank Holiday Configuration ────────────────────────────────────────── */}
      <Card className="p-6">
        <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200 mb-4">
          Bank Holiday Configuration
        </h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
          When a country is set, that channel's forecast will be zeroed out on public holidays.
        </p>

        <div className="flex flex-wrap gap-3 items-end">
          <div className="flex-1 min-w-40">
            <label className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-1 block">Channel</label>
            <select value={holChannel} onChange={(e) => setHolChannel(e.target.value)} className={inputCls}>
              <option value="">Select channel…</option>
              {channelNames.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div className="flex-1 min-w-40">
            <label className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-1 block">Country</label>
            <select value={holCountry} onChange={(e) => setHolCountry(e.target.value)} className={inputCls}>
              {Object.entries(COUNTRIES).map(([code, name]) => (
                <option key={code} value={code}>{name} ({code})</option>
              ))}
            </select>
          </div>
          <Button onClick={handleSetHoliday} loading={setHoliday.isPending} disabled={!holChannel}>Save</Button>
        </div>

        {config && Object.keys(config.holidays).length > 0 && (
          <div className="mt-4 space-y-2">
            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Current</p>
            {Object.entries(config.holidays).map(([ch, cc]) => (
              <div key={ch} className="flex items-center justify-between rounded-lg bg-slate-50 dark:bg-slate-800/50 px-3 py-2">
                <span className="text-sm text-slate-700 dark:text-slate-300">
                  <strong>{ch}</strong> → {COUNTRIES[cc] ?? cc} ({cc})
                </span>
                <button onClick={() => deleteHoliday.mutate(ch)} className="text-slate-400 hover:text-red-500 transition-colors" title="Remove">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* ── Monthly Volume Targets ────────────────────────────────────────────── */}
      <Card className="p-6">
        <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200 mb-4">
          Monthly Volume Targets
        </h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
          Override a specific month's total forecast volume. The model's daily pattern will be scaled to hit the target.
        </p>

        <div className="flex flex-wrap gap-3 items-end mb-4">
          <div className="flex-1 min-w-40">
            <label className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-1 block">Channel</label>
            <select value={tgtChannel} onChange={(e) => setTgtChannel(e.target.value)} className={inputCls}>
              <option value="">Select channel…</option>
              {channelNames.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div className="w-32">
            <label className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-1 block">Year</label>
            <select value={tgtYear} onChange={(e) => setTgtYear(Number(e.target.value))} className={inputCls}>
              {yearOptions.map((y) => <option key={y} value={y}>{y}</option>)}
            </select>
          </div>
        </div>

        {tgtChannel && (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 mb-4">
              {MONTH_NAMES.map((name, i) => {
                const monthKey = `${tgtYear}-${String(i + 1).padStart(2, '0')}`
                return (
                  <div key={monthKey} className="rounded-lg bg-slate-50 dark:bg-slate-800/50 p-3">
                    <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1.5">{name}</p>
                    <input
                      type="number" placeholder="—"
                      value={tgtValues[monthKey] ?? ''}
                      onChange={(e) => setTgtValues((v) => ({ ...v, [monthKey]: e.target.value }))}
                      className="w-full rounded border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                )
              })}
            </div>
            <Button onClick={handleSaveTargets} loading={setTargets.isPending} disabled={!tgtChannel}>
              Save targets
            </Button>
          </>
        )}

        {config && Object.keys(config.targets).length > 0 && (
          <div className="mt-5 space-y-3">
            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">Current Targets</p>
            {Object.entries(config.targets).map(([ch, months]) => (
              <div key={ch} className="rounded-lg bg-slate-50 dark:bg-slate-800/50 px-3 py-2">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-semibold text-slate-700 dark:text-slate-300">{ch}</span>
                  <button onClick={() => deleteTargets.mutate(ch)} className="text-slate-400 hover:text-red-500 transition-colors" title="Remove all targets">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(months as Record<string, number>).sort().map(([m, v]) => (
                    <span key={m} className="text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 px-2 py-0.5 rounded-full">
                      {m}: {v.toLocaleString()}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* ── Hiring Waves ──────────────────────────────────────────────────────── */}
      <Card className="p-6">
        <div className="flex items-center gap-2 mb-1">
          <Users className="w-5 h-5 text-indigo-500" />
          <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200">Hiring Waves</h2>
        </div>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-5">
          Define periods when new junior agents are onboarded. The AHT model uses the junior ratio to
          account for higher handle times during the learning curve.
        </p>

        <div className="space-y-4 mb-5">
          <div className="flex flex-wrap gap-3 items-end">
            <div className="flex-1 min-w-40">
              <label className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-1 block">Channel</label>
              <select value={waveChannel} onChange={(e) => setWaveChannel(e.target.value)} className={inputCls}>
                <option value="">Select channel…</option>
                {channelNames.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div className="flex-1 min-w-40">
              <label className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-1 block">Label (optional)</label>
              <input
                type="text" placeholder="e.g. Q1 intake"
                value={waveForm.label}
                onChange={(e) => setWaveForm((v) => ({ ...v, label: e.target.value }))}
                className={inputCls}
              />
            </div>
          </div>

          <div className="flex flex-wrap gap-3 items-end">
            <div className="flex-1 min-w-36">
              <label className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-1 block">Start Date</label>
              <input
                type="date"
                value={waveForm.start_date}
                onChange={(e) => setWaveForm((v) => ({ ...v, start_date: e.target.value }))}
                className={inputCls}
              />
            </div>
            <div className="flex-1 min-w-36">
              <label className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-1 block">End Date</label>
              <input
                type="date"
                value={waveForm.end_date}
                onChange={(e) => setWaveForm((v) => ({ ...v, end_date: e.target.value }))}
                className={inputCls}
              />
            </div>
            <div className="w-36">
              <label className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-1 block">Junior Agents</label>
              <input
                type="number" min="0" placeholder="e.g. 10"
                value={waveForm.junior_count}
                onChange={(e) => setWaveForm((v) => ({ ...v, junior_count: e.target.value }))}
                className={inputCls}
              />
            </div>
            <div className="w-36">
              <label className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-1 block">Total Agents</label>
              <input
                type="number" min="1" placeholder="e.g. 40"
                value={waveForm.total_agents}
                onChange={(e) => setWaveForm((v) => ({ ...v, total_agents: e.target.value }))}
                className={inputCls}
              />
            </div>
          </div>

          {waveJuniorRatio !== null && !isNaN(waveJuniorRatio) && waveJuniorRatio >= 0 && waveJuniorRatio <= 1 && (
            <p className="text-xs text-indigo-600 dark:text-indigo-400">
              Junior ratio: <strong>{(waveJuniorRatio * 100).toFixed(1)}%</strong>
            </p>
          )}

          {waveError && (
            <p className="text-sm text-red-500">{waveError}</p>
          )}

          <Button onClick={handleCreateWave} loading={createWaveMut.isPending} disabled={!waveChannel}>
            Add Hiring Wave
          </Button>
        </div>

        {waveChannel && wavesForChannel.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
              Waves for {waveChannel}
            </p>
            {wavesForChannel
              .sort((a, b) => a.start_date.localeCompare(b.start_date))
              .map((w) => (
                <div key={w.id} className="flex items-center justify-between rounded-lg bg-slate-50 dark:bg-slate-800/50 px-3 py-2.5 gap-3">
                  <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-slate-700 dark:text-slate-300">
                    <span>
                      <strong>{w.start_date}</strong> → <strong>{w.end_date}</strong>
                      {w.label && <span className="ml-2 text-slate-500 dark:text-slate-400">({w.label})</span>}
                    </span>
                    <span className="text-indigo-600 dark:text-indigo-400">
                      {w.junior_count}/{w.total_agents} juniors ({(w.junior_ratio * 100).toFixed(0)}%)
                    </span>
                  </div>
                  <button
                    onClick={() => { if (confirm('Delete this hiring wave?')) deleteWaveMut.mutate(w.id) }}
                    className="text-slate-400 hover:text-red-500 transition-colors flex-shrink-0"
                    title="Delete"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
          </div>
        )}

        {waveChannel && wavesForChannel.length === 0 && (
          <p className="text-sm text-slate-400">No hiring waves for {waveChannel} yet.</p>
        )}
      </Card>
    </div>
  )
}
