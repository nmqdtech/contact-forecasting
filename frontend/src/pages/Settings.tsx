import { useState } from 'react'
import { Trash2 } from 'lucide-react'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import { useChannels } from '../hooks/useChannels'
import { useConfig, useDeleteHoliday, useDeleteTargets, useSetHoliday, useSetTargets } from '../hooks/useConfig'

const COUNTRIES: Record<string, string> = {
  GB: 'United Kingdom', US: 'United States', FR: 'France', DE: 'Germany',
  ES: 'Spain', IT: 'Italy', NL: 'Netherlands', BE: 'Belgium', MA: 'Morocco',
  CA: 'Canada', AU: 'Australia', PT: 'Portugal', IE: 'Ireland',
  SE: 'Sweden', NO: 'Norway', DK: 'Denmark', CH: 'Switzerland',
  AE: 'United Arab Emirates', SA: 'Saudi Arabia', ZA: 'South Africa',
}

export default function Settings() {
  const { data: channels } = useChannels()
  const { data: config } = useConfig()

  // Holiday state
  const [holChannel, setHolChannel] = useState('')
  const [holCountry, setHolCountry] = useState('GB')
  const setHoliday = useSetHoliday()
  const deleteHoliday = useDeleteHoliday()

  // Targets state
  const [tgtChannel, setTgtChannel] = useState('')
  const [tgtMonth, setTgtMonth] = useState('')
  const [tgtVolume, setTgtVolume] = useState('')
  const setTargets = useSetTargets()
  const deleteTargets = useDeleteTargets()

  const channelNames = channels?.map((c) => c.name) ?? []

  const handleSetHoliday = () => {
    if (!holChannel) return
    setHoliday.mutate({ channel: holChannel, country_code: holCountry })
  }

  const handleSetTarget = () => {
    if (!tgtChannel || !tgtMonth || !tgtVolume) return
    setTargets.mutate({ channel: tgtChannel, targets: { [tgtMonth]: Number(tgtVolume) } })
    setTgtMonth('')
    setTgtVolume('')
  }

  const inputCls =
    'block w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500'

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

      {/* Monthly targets */}
      <Card className="p-6">
        <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200 mb-4">
          Monthly Volume Targets
        </h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 mb-4">
          Override a specific month's total forecast volume. The model's daily pattern will be
          scaled to hit the target.
        </p>

        <div className="flex flex-wrap gap-3 items-end">
          <div className="flex-1 min-w-40">
            <label className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-1 block">Channel</label>
            <select value={tgtChannel} onChange={(e) => setTgtChannel(e.target.value)} className={inputCls}>
              <option value="">Select channel…</option>
              {channelNames.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div className="w-36">
            <label className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-1 block">Month (YYYY-MM)</label>
            <input
              type="month"
              value={tgtMonth}
              onChange={(e) => setTgtMonth(e.target.value)}
              className={inputCls}
            />
          </div>
          <div className="w-36">
            <label className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-1 block">Volume</label>
            <input
              type="number"
              placeholder="e.g. 35000"
              value={tgtVolume}
              onChange={(e) => setTgtVolume(e.target.value)}
              className={inputCls}
            />
          </div>
          <Button
            onClick={handleSetTarget}
            loading={setTargets.isPending}
            disabled={!tgtChannel || !tgtMonth || !tgtVolume}
          >
            Add
          </Button>
        </div>

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
                  {Object.entries(months).sort().map(([m, v]) => (
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
