import { useEffect, useState } from 'react'
import { Trash2 } from 'lucide-react'
import { QRCodeSVG } from 'qrcode.react'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import { useChannels } from '../hooks/useChannels'
import { useConfig, useDeleteHoliday, useDeleteTargets, useSetHoliday, useSetTargets } from '../hooks/useConfig'
import { setupTotp, enableTotp, disableTotp, type TotpSetupResponse } from '../api/auth'
import { useAuthStore } from '../store/useAuthStore'

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

  // Holiday state
  const [holChannel, setHolChannel] = useState('')
  const [holCountry, setHolCountry] = useState('GB')
  const setHoliday = useSetHoliday()
  const deleteHoliday = useDeleteHoliday()

  // Targets state
  const currentYear = new Date().getFullYear()
  const [tgtChannel, setTgtChannel] = useState('')
  const [tgtYear, setTgtYear] = useState(currentYear)
  const [tgtValues, setTgtValues] = useState<Record<string, string>>({})
  const setTargets = useSetTargets()
  const deleteTargets = useDeleteTargets()

  // Pre-populate grid from existing config when channel/year changes
  useEffect(() => {
    if (!tgtChannel || !config) {
      setTgtValues({})
      return
    }
    const channelTargets = (config.targets[tgtChannel] ?? {}) as Record<string, number>
    const populated: Record<string, string> = {}
    for (const [month, vol] of Object.entries(channelTargets)) {
      if (month.startsWith(`${tgtYear}-`)) {
        populated[month] = String(vol)
      }
    }
    setTgtValues(populated)
  }, [tgtChannel, tgtYear, config])

  const channelNames = channels?.map((c) => c.name) ?? []

  // 2FA state
  const user = useAuthStore((s) => s.user)
  const setTotpEnabled = useAuthStore((s) => s.setTotpEnabled)
  const [totpSetup, setTotpSetup] = useState<TotpSetupResponse | null>(null)
  const [totpCode, setTotpCode] = useState('')
  const [totpLoading, setTotpLoading] = useState(false)
  const [totpError, setTotpError] = useState('')

  const handleSetupTotp = async () => {
    setTotpLoading(true)
    setTotpError('')
    try {
      const data = await setupTotp()
      setTotpSetup(data)
      setTotpCode('')
    } catch {
      setTotpError('Failed to set up 2FA')
    } finally {
      setTotpLoading(false)
    }
  }

  const handleEnableTotp = async () => {
    setTotpLoading(true)
    setTotpError('')
    try {
      await enableTotp(totpCode)
      setTotpEnabled(true)
      setTotpSetup(null)
      setTotpCode('')
    } catch {
      setTotpError('Invalid code — try again')
    } finally {
      setTotpLoading(false)
    }
  }

  const handleDisableTotp = async () => {
    setTotpLoading(true)
    setTotpError('')
    try {
      await disableTotp()
      setTotpEnabled(false)
    } catch {
      setTotpError('Failed to disable 2FA')
    } finally {
      setTotpLoading(false)
    }
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
      if (vol !== '' && !isNaN(n) && n > 0) {
        targets[month] = n
      }
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
          Configure bank holidays and monthly volume targets per channel
        </p>
      </div>

      {/* Holiday config */}
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
          <Button
            onClick={handleSetHoliday}
            loading={setHoliday.isPending}
            disabled={!holChannel}
          >
            Save
          </Button>
        </div>

        {/* Current configs */}
        {config && Object.keys(config.holidays).length > 0 && (
          <div className="mt-4 space-y-2">
            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
              Current
            </p>
            {Object.entries(config.holidays).map(([ch, cc]) => (
              <div
                key={ch}
                className="flex items-center justify-between rounded-lg bg-slate-50 dark:bg-slate-800/50 px-3 py-2"
              >
                <span className="text-sm text-slate-700 dark:text-slate-300">
                  <strong>{ch}</strong> → {COUNTRIES[cc] ?? cc} ({cc})
                </span>
                <button
                  onClick={() => deleteHoliday.mutate(ch)}
                  className="text-slate-400 hover:text-red-500 transition-colors"
                  title="Remove"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Two-Factor Authentication */}
      <Card className="p-6">
        <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200 mb-1">
          Two-Factor Authentication
        </h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
          Add an extra layer of security using an authenticator app (Google Authenticator, Authy).
        </p>

        {totpError && (
          <div className="mb-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-sm px-3 py-2 rounded-lg">
            {totpError}
          </div>
        )}

        {user?.totp_enabled ? (
          <div className="flex items-center gap-4">
            <span className="text-sm text-emerald-600 dark:text-emerald-400 font-medium">
              ✓ 2FA is enabled
            </span>
            <Button
              variant="secondary"
              loading={totpLoading}
              onClick={handleDisableTotp}
            >
              Disable 2FA
            </Button>
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
                  <code className="text-xs bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded break-all">
                    {totpSetup.secret}
                  </code>
                </div>
                <div className="space-y-2">
                  <input
                    type="text"
                    inputMode="numeric"
                    pattern="[0-9]{6}"
                    maxLength={6}
                    placeholder="6-digit code"
                    value={totpCode}
                    onChange={(e) => setTotpCode(e.target.value)}
                    className={inputCls}
                  />
                  <div className="flex gap-2">
                    <Button
                      onClick={handleEnableTotp}
                      loading={totpLoading}
                      disabled={totpCode.length !== 6}
                    >
                      Verify & Enable
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={() => { setTotpSetup(null); setTotpError('') }}
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <Button loading={totpLoading} onClick={handleSetupTotp}>
            Set up 2FA
          </Button>
        )}
      </Card>

      {/* Monthly targets */}
      <Card className="p-6">
        <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200 mb-4">
          Monthly Volume Targets
        </h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
          Override a specific month's total forecast volume. The model's daily pattern will be
          scaled to hit the target.
        </p>

        {/* Channel + Year selectors */}
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
            <select
              value={tgtYear}
              onChange={(e) => setTgtYear(Number(e.target.value))}
              className={inputCls}
            >
              {yearOptions.map((y) => <option key={y} value={y}>{y}</option>)}
            </select>
          </div>
        </div>

        {/* 12-month grid */}
        {tgtChannel && (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 mb-4">
              {MONTH_NAMES.map((name, i) => {
                const monthKey = `${tgtYear}-${String(i + 1).padStart(2, '0')}`
                return (
                  <div key={monthKey} className="rounded-lg bg-slate-50 dark:bg-slate-800/50 p-3">
                    <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1.5">{name}</p>
                    <input
                      type="number"
                      placeholder="—"
                      value={tgtValues[monthKey] ?? ''}
                      onChange={(e) =>
                        setTgtValues((v) => ({ ...v, [monthKey]: e.target.value }))
                      }
                      className="w-full rounded border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                )
              })}
            </div>
            <Button
              onClick={handleSaveTargets}
              loading={setTargets.isPending}
              disabled={!tgtChannel}
            >
              Save targets
            </Button>
          </>
        )}

        {/* Current targets */}
        {config && Object.keys(config.targets).length > 0 && (
          <div className="mt-5 space-y-3">
            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
              Current Targets
            </p>
            {Object.entries(config.targets).map(([ch, months]) => (
              <div key={ch} className="rounded-lg bg-slate-50 dark:bg-slate-800/50 px-3 py-2">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-semibold text-slate-700 dark:text-slate-300">{ch}</span>
                  <button
                    onClick={() => deleteTargets.mutate(ch)}
                    className="text-slate-400 hover:text-red-500 transition-colors"
                    title="Remove all targets"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(months as Record<string, number>).sort().map(([m, v]) => (
                    <span
                      key={m}
                      className="text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 px-2 py-0.5 rounded-full"
                    >
                      {m}: {v.toLocaleString()}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}
