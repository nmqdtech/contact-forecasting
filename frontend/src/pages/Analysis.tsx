import { useMemo, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import Card from '../components/ui/Card'
import SeasonalityChart from '../components/charts/SeasonalityChart'
import { useChannelData, useChannels } from '../hooks/useChannels'
import { useMonthlyForecast, useSeasonality } from '../hooks/useForecasts'
import type { ObservationPoint } from '../types'

const fmt = (n: number) => n.toLocaleString(undefined, { maximumFractionDigits: 0 })

const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/** Return ISO week number for a Date */
function isoWeek(d: Date): number {
  const tmp = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()))
  tmp.setUTCDate(tmp.getUTCDate() + 4 - (tmp.getUTCDay() || 7))
  const yearStart = new Date(Date.UTC(tmp.getUTCFullYear(), 0, 1))
  return Math.ceil(((tmp.getTime() - yearStart.getTime()) / 86400000 + 1) / 7)
}

function isoWeekYear(d: Date): number {
  const tmp = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()))
  tmp.setUTCDate(tmp.getUTCDate() + 4 - (tmp.getUTCDay() || 7))
  return tmp.getUTCFullYear()
}

/** Get YYYY-WNN string for a Date */
function weekKey(d: Date): string {
  const yr = isoWeekYear(d)
  const wk = isoWeek(d)
  return `${yr}-W${String(wk).padStart(2, '0')}`
}

/** Parse YYYY-WNN into { year, week } */
function parseWeekInput(val: string): { year: number; week: number } | null {
  const m = val.match(/^(\d{4})-W(\d{2})$/)
  if (!m) return null
  return { year: Number(m[1]), week: Number(m[2]) }
}

/** Get Mon–Sun dates for a given ISO year+week */
function weekDates(year: number, week: number): Date[] {
  // Jan 4 is always in week 1
  const jan4 = new Date(Date.UTC(year, 0, 4))
  const dayOfWeek = (jan4.getUTCDay() + 6) % 7 // 0=Mon
  const monday = new Date(jan4)
  monday.setUTCDate(jan4.getUTCDate() - dayOfWeek + (week - 1) * 7)
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(monday)
    d.setUTCDate(monday.getUTCDate() + i)
    return d
  })
}

function toDateStr(d: Date): string {
  return d.toISOString().slice(0, 10)
}

interface WoWRow {
  day: string
  current: number | null
  prior: number | null
}

function buildWoW(obs: ObservationPoint[], year: number, week: number): WoWRow[] {
  const map = new Map(obs.map((o) => [o.date, o.volume]))
  const currentDates = weekDates(year, week)
  const priorDates = weekDates(week === 1 ? year - 1 : year, week === 1 ? 52 : week - 1)
  return DAY_NAMES.map((day, i) => ({
    day,
    current: map.get(toDateStr(currentDates[i])) ?? null,
    prior: map.get(toDateStr(priorDates[i])) ?? null,
  }))
}

function buildYoY(obs: ObservationPoint[], year: number, week: number): WoWRow[] | null {
  const map = new Map(obs.map((o) => [o.date, o.volume]))
  const currentDates = weekDates(year, week)
  const priorDates = weekDates(year - 1, week)
  // Check if any prior year data exists
  const hasPrior = priorDates.some((d) => map.has(toDateStr(d)))
  if (!hasPrior) return null
  return DAY_NAMES.map((day, i) => ({
    day,
    current: map.get(toDateStr(currentDates[i])) ?? null,
    prior: map.get(toDateStr(priorDates[i])) ?? null,
  }))
}

function sumNonNull(rows: WoWRow[], key: 'current' | 'prior'): number {
  return rows.reduce((acc, r) => acc + (r[key] ?? 0), 0)
}

export default function Analysis() {
  const { data: channels } = useChannels()
  const [activeChannel, setActiveChannel] = useState<string | null>(null)

  const channel = activeChannel ?? channels?.[0]?.name ?? null
  const { data: seasonality, isLoading: seaLoading } = useSeasonality(channel)
  const { data: channelObs } = useChannelData(channel)
  const { data: monthly } = useMonthlyForecast(channel)

  // Default week = current ISO week
  const today = new Date()
  const defaultWeek = weekKey(today)
  const [selectedWeek, setSelectedWeek] = useState(defaultWeek)

  const parsed = useMemo(() => parseWeekInput(selectedWeek), [selectedWeek])

  const wowData = useMemo<WoWRow[] | null>(() => {
    if (!channelObs || !parsed) return null
    return buildWoW(channelObs, parsed.year, parsed.week)
  }, [channelObs, parsed])

  const yoyData = useMemo<WoWRow[] | null>(() => {
    if (!channelObs || !parsed) return null
    return buildYoY(channelObs, parsed.year, parsed.week)
  }, [channelObs, parsed])

  // Monthly forecast vs historical — merge by month label
  const monthlyChartData = useMemo(() => {
    if (!monthly) return []
    const histMap = new Map(monthly.historical.map((h) => [h.month, h.total]))
    return monthly.forecast.map((f) => ({
      month: MONTH_NAMES[Number(f.month.slice(5, 7)) - 1] + ' ' + f.month.slice(0, 4),
      Forecast: Math.round(f.total),
      Historical: Math.round(histMap.get(f.month) ?? 0) || undefined,
    }))
  }, [monthly])

  if (!channels || channels.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <p className="text-slate-500 dark:text-slate-400">
          No channels available — upload data and train models first.
        </p>
      </div>
    )
  }

  const wowTotal = wowData ? sumNonNull(wowData, 'current') : 0
  const wowPriorTotal = wowData ? sumNonNull(wowData, 'prior') : 0
  const wowChangePct = wowPriorTotal > 0 ? ((wowTotal - wowPriorTotal) / wowPriorTotal) * 100 : null

  const yoyTotal = yoyData ? sumNonNull(yoyData, 'current') : 0
  const yoyPriorTotal = yoyData ? sumNonNull(yoyData, 'prior') : 0
  const yoyChangePct = yoyPriorTotal > 0 ? ((yoyTotal - yoyPriorTotal) / yoyPriorTotal) * 100 : null

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Analysis</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Week-over-week, year-over-year, and monthly comparisons
        </p>
      </div>

      {/* Channel selector */}
      <div className="flex gap-2 flex-wrap">
        {channels.map((ch) => (
          <button
            key={ch.name}
            onClick={() => setActiveChannel(ch.name)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              channel === ch.name
                ? 'bg-blue-600 text-white'
                : 'bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700'
            }`}
          >
            {ch.name}
          </button>
        ))}
      </div>

      {channel && (
        <>
          {/* Week selector */}
          <div className="flex items-center gap-3">
            <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
              Reference week:
            </label>
            <input
              type="week"
              value={selectedWeek}
              onChange={(e) => setSelectedWeek(e.target.value)}
              className="rounded border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-sm text-slate-800 dark:text-slate-200 px-3 py-1.5"
            />
          </div>

          {/* A. Week-over-Week */}
          <Card className="p-5">
            <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200 mb-1">
              Week-over-Week — {channel}
            </h2>
            {wowData ? (
              <>
                <div className="flex flex-wrap gap-4 text-sm text-slate-600 dark:text-slate-400 mb-4">
                  <span>This week: <strong className="text-slate-800 dark:text-slate-200">{fmt(wowTotal)}</strong></span>
                  <span>Prior week: <strong className="text-slate-800 dark:text-slate-200">{fmt(wowPriorTotal)}</strong></span>
                  {wowChangePct !== null && (
                    <span className={wowChangePct >= 0 ? 'text-emerald-600 dark:text-emerald-400 font-semibold' : 'text-red-600 dark:text-red-400 font-semibold'}>
                      {wowChangePct >= 0 ? '+' : ''}{wowChangePct.toFixed(1)}%
                    </span>
                  )}
                </div>
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={wowData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                    <XAxis dataKey="day" tick={{ fontSize: 11 }} />
                    <YAxis tickFormatter={fmt} width={72} tick={{ fontSize: 11 }} />
                    <Tooltip formatter={(v: number) => fmt(v)} />
                    <Legend />
                    <Bar dataKey="current" name="This week" fill="#2563EB" radius={[3, 3, 0, 0]} />
                    <Bar dataKey="prior" name="Prior week" fill="#94A3B8" radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </>
            ) : (
              <p className="text-sm text-slate-400 dark:text-slate-500">No observation data available.</p>
            )}
          </Card>

          {/* B. Year-over-Year */}
          <Card className="p-5">
            <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200 mb-1">
              Year-over-Year — {channel}
            </h2>
            {yoyData ? (
              <>
                <div className="flex flex-wrap gap-4 text-sm text-slate-600 dark:text-slate-400 mb-4">
                  <span>This year: <strong className="text-slate-800 dark:text-slate-200">{fmt(yoyTotal)}</strong></span>
                  <span>Last year: <strong className="text-slate-800 dark:text-slate-200">{fmt(yoyPriorTotal)}</strong></span>
                  {yoyChangePct !== null && (
                    <span className={yoyChangePct >= 0 ? 'text-emerald-600 dark:text-emerald-400 font-semibold' : 'text-red-600 dark:text-red-400 font-semibold'}>
                      {yoyChangePct >= 0 ? '+' : ''}{yoyChangePct.toFixed(1)}%
                    </span>
                  )}
                </div>
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={yoyData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                    <XAxis dataKey="day" tick={{ fontSize: 11 }} />
                    <YAxis tickFormatter={fmt} width={72} tick={{ fontSize: 11 }} />
                    <Tooltip formatter={(v: number) => fmt(v)} />
                    <Legend />
                    <Bar dataKey="current" name="This year" fill="#2563EB" radius={[3, 3, 0, 0]} />
                    <Bar dataKey="prior" name="Last year" fill="#94A3B8" radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </>
            ) : (
              <p className="text-sm text-slate-400 dark:text-slate-500">
                Insufficient data — less than one year of history available.
              </p>
            )}
          </Card>

          {/* C. Monthly Forecast vs Historical */}
          {monthlyChartData.length > 0 && (
            <Card className="p-5">
              <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200 mb-4">
                Monthly: Forecast vs Historical — {channel}
              </h2>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={monthlyChartData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                  <XAxis dataKey="month" tick={{ fontSize: 10 }} interval={0} angle={-35} textAnchor="end" height={52} />
                  <YAxis tickFormatter={fmt} width={72} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(v: number) => fmt(v)} />
                  <Legend />
                  <Bar dataKey="Historical" fill="#2563EB" radius={[3, 3, 0, 0]} />
                  <Bar dataKey="Forecast" fill="#F59E0B" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>

              {/* Table */}
              <div className="overflow-x-auto mt-5">
                <table className="min-w-full text-sm text-slate-700 dark:text-slate-300">
                  <thead>
                    <tr className="border-b border-slate-200 dark:border-slate-700 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">
                      <th className="pb-2 pr-4 text-left">Month</th>
                      <th className="pb-2 px-4 text-right">Historical</th>
                      <th className="pb-2 px-4 text-right">Forecast</th>
                      <th className="pb-2 pl-4 text-right">Change</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {monthlyChartData.map((row) => {
                      const change =
                        row.Historical && row.Historical > 0
                          ? ((row.Forecast - row.Historical) / row.Historical) * 100
                          : null
                      return (
                        <tr key={row.month} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                          <td className="py-1.5 pr-4 font-medium">{row.month}</td>
                          <td className="py-1.5 px-4 text-right tabular-nums">
                            {row.Historical ? fmt(row.Historical) : '—'}
                          </td>
                          <td className="py-1.5 px-4 text-right tabular-nums">{fmt(row.Forecast)}</td>
                          <td
                            className={`py-1.5 pl-4 text-right tabular-nums font-semibold ${
                              change === null
                                ? 'text-slate-400'
                                : change >= 0
                                ? 'text-emerald-600 dark:text-emerald-400'
                                : 'text-red-600 dark:text-red-400'
                            }`}
                          >
                            {change === null ? '—' : `${change >= 0 ? '+' : ''}${change.toFixed(1)}%`}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </Card>
          )}

          {/* D. Seasonality */}
          <Card className="p-5">
            <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200 mb-5">
              Seasonal Patterns — {channel}
            </h2>
            {seaLoading ? (
              <div className="h-60 flex items-center justify-center text-slate-400">Loading…</div>
            ) : seasonality ? (
              <SeasonalityChart
                monthlyFactors={seasonality.monthly_factors}
                weeklyPattern={seasonality.weekly_pattern}
              />
            ) : (
              <div className="h-40 flex items-center justify-center text-slate-400 text-sm">
                No seasonality data — train a model first.
              </div>
            )}
          </Card>

          {seasonality && (
            <Card className="p-5">
              <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200 mb-3">
                Monthly Factor Table
              </h2>
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm text-slate-700 dark:text-slate-300">
                  <thead>
                    <tr className="border-b border-slate-200 dark:border-slate-700">
                      {['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'].map((m) => (
                        <th key={m} className="pb-2 px-2 text-center font-semibold text-slate-500 dark:text-slate-400 text-xs">
                          {m}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      {Object.entries(seasonality.monthly_factors)
                        .sort(([a], [b]) => Number(a) - Number(b))
                        .map(([m, factor]) => (
                          <td key={m} className="pt-2 px-2 text-center">
                            <span
                              className={`font-semibold ${
                                factor > 1.05
                                  ? 'text-blue-600 dark:text-blue-400'
                                  : factor < 0.95
                                  ? 'text-red-500 dark:text-red-400'
                                  : 'text-slate-600 dark:text-slate-300'
                              }`}
                            >
                              {factor.toFixed(2)}
                            </span>
                          </td>
                        ))}
                    </tr>
                  </tbody>
                </table>
              </div>
              <p className="text-xs text-slate-400 dark:text-slate-500 mt-2">
                Values above 1.0 indicate higher-than-average volume; below 1.0 indicates lower.
              </p>
            </Card>
          )}
        </>
      )}
    </div>
  )
}
