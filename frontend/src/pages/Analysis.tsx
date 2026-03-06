import { useEffect, useMemo, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import Card from '../components/ui/Card'
import SeasonalityChart from '../components/charts/SeasonalityChart'
import { useChannelData, useChannelHourly, useChannels } from '../hooks/useChannels'
import { useMonthlyForecast, useSeasonality } from '../hooks/useForecasts'
import type { ObservationPoint } from '../types'

const WEEK_OPTIONS = Array.from({ length: 53 }, (_, i) => i + 1)
const fmtHour = (h: number) => h === 0 ? '12AM' : h < 12 ? `${h}AM` : h === 12 ? '12PM' : `${h - 12}PM`

// ─── Formatters ───────────────────────────────────────────────────────────────

const fmt = (n: number) => n.toLocaleString(undefined, { maximumFractionDigits: 0 })

const fmtPct = (n: number) =>
  `${n >= 0 ? '+' : ''}${n.toFixed(1)}%`

const changeCls = (v: number | null) =>
  v === null
    ? 'text-slate-400'
    : v >= 0
    ? 'text-emerald-600 dark:text-emerald-400 font-semibold'
    : 'text-red-600 dark:text-red-400 font-semibold'

// ─── ISO week helpers ─────────────────────────────────────────────────────────

const DAY_NAMES  = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const MONTH_ABBR = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

function isoWeekYear(d: Date): number {
  const t = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()))
  t.setUTCDate(t.getUTCDate() + 4 - (t.getUTCDay() || 7))
  return t.getUTCFullYear()
}

function isoWeekNum(d: Date): number {
  const t = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()))
  t.setUTCDate(t.getUTCDate() + 4 - (t.getUTCDay() || 7))
  const yearStart = new Date(Date.UTC(t.getUTCFullYear(), 0, 1))
  return Math.ceil(((t.getTime() - yearStart.getTime()) / 86400000 + 1) / 7)
}

function weekKey(d: Date): string {
  return `${isoWeekYear(d)}-W${String(isoWeekNum(d)).padStart(2, '0')}`
}

function parseWeekInput(val: string): { year: number; week: number } | null {
  const m = val.match(/^(\d{4})-W(\d{1,2})$/)
  if (!m) return null
  return { year: Number(m[1]), week: Number(m[2]) }
}

/** Returns Mon–Sun Date[] for an ISO year+week. */
function weekDates(year: number, week: number): Date[] {
  const jan4 = new Date(Date.UTC(year, 0, 4))
  const dow  = (jan4.getUTCDay() + 6) % 7 // 0 = Mon
  const mon  = new Date(jan4)
  mon.setUTCDate(jan4.getUTCDate() - dow + (week - 1) * 7)
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(mon)
    d.setUTCDate(mon.getUTCDate() + i)
    return d
  })
}

function toDateStr(d: Date): string {
  return d.toISOString().slice(0, 10)
}

// ─── Week-set parser ──────────────────────────────────────────────────────────
// Supports: "W01", "3", "W03-W08", "5-10", and comma-separated mixes.

function parseWeekSet(raw: string): number[] {
  const weeks = new Set<number>()
  raw.split(',').forEach((part) => {
    const s = part.trim().replace(/^W/i, '')
    if (s.includes('-')) {
      const [a, b] = s.split('-').map((x) => parseInt(x.replace(/^W/i, '').trim(), 10))
      if (!isNaN(a) && !isNaN(b) && a >= 1 && b <= 53)
        for (let w = a; w <= b; w++) weeks.add(w)
    } else {
      const w = parseInt(s, 10)
      if (!isNaN(w) && w >= 1 && w <= 53) weeks.add(w)
    }
  })
  return Array.from(weeks).sort((a, b) => a - b)
}

// ─── Data builders ────────────────────────────────────────────────────────────

interface DayRow { day: string; A: number | null; B: number | null }

function buildDailyComparison(
  obs: ObservationPoint[],
  wkA: { year: number; week: number } | null,
  wkB: { year: number; week: number } | null,
): DayRow[] {
  const map   = new Map(obs.map((o) => [o.date, o.volume]))
  const datesA = wkA ? weekDates(wkA.year, wkA.week) : null
  const datesB = wkB ? weekDates(wkB.year, wkB.week) : null
  return DAY_NAMES.map((day, i) => ({
    day,
    A: datesA ? (map.get(toDateStr(datesA[i])) ?? null) : null,
    B: datesB ? (map.get(toDateStr(datesB[i])) ?? null) : null,
  }))
}

interface WeekRow { week: string; A: number; B: number }

function buildMultiWeek(
  obs: ObservationPoint[],
  yearA: number,
  yearB: number,
  weeks: number[],
): WeekRow[] {
  const map = new Map(obs.map((o) => [o.date, o.volume]))
  return weeks.map((w) => {
    const label  = `W${String(w).padStart(2, '0')}`
    const totalA = weekDates(yearA, w).reduce((s, d) => s + (map.get(toDateStr(d)) ?? 0), 0)
    const totalB = weekDates(yearB, w).reduce((s, d) => s + (map.get(toDateStr(d)) ?? 0), 0)
    return { week: label, A: Math.round(totalA), B: Math.round(totalB) }
  })
}

// ─── Small shared components ──────────────────────────────────────────────────

function StatChip({ label, value, highlight }: { label: string; value: string; highlight?: string }) {
  return (
    <span className="text-sm text-slate-600 dark:text-slate-400">
      {label}:{' '}
      <strong className={highlight ?? 'text-slate-800 dark:text-slate-200'}>{value}</strong>
    </span>
  )
}

function ModeTab({
  active, label, onClick,
}: { active: boolean; label: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
        active
          ? 'bg-blue-600 text-white'
          : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600'
      }`}
    >
      {label}
    </button>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function Analysis() {
  const { data: channels } = useChannels()
  const [activeChannel, setActiveChannel] = useState<string | null>(null)

  const channel = activeChannel ?? channels?.[0]?.name ?? null
  const isHourly = channels?.find((c) => c.name === channel)?.is_hourly ?? false
  const { data: seasonality, isLoading: seaLoading } = useSeasonality(channel)
  const { data: channelObs } = useChannelData(channel)
  const { data: monthly } = useMonthlyForecast(channel)
  const { data: hourlyPattern } = useChannelHourly(isHourly ? channel : null)

  // Years available in the loaded data (for dropdowns)
  const availableYears = useMemo(() => {
    const ys = new Set<string>()
    for (const o of channelObs ?? []) ys.add(o.date.slice(0, 4))
    return [...ys].sort().reverse()
  }, [channelObs])

  // ── Section 1: Single-week comparison ──────────────────────────────────────
  const today = new Date()
  const defaultWeekA = weekKey(today)
  const defaultWeekB = (() => {
    const d = new Date(today)
    d.setFullYear(d.getFullYear() - 1)
    return weekKey(d)
  })()

  const [weekA, setWeekA] = useState(defaultWeekA)
  const [weekB, setWeekB] = useState(defaultWeekB)

  const parsedA = useMemo(() => parseWeekInput(weekA), [weekA])
  const parsedB = useMemo(() => parseWeekInput(weekB), [weekB])

  const dailyData = useMemo<DayRow[]>(() => {
    if (!channelObs) return []
    return buildDailyComparison(channelObs, parsedA, parsedB)
  }, [channelObs, parsedA, parsedB])

  const totalA = dailyData.reduce((s, r) => s + (r.A ?? 0), 0)
  const totalB = dailyData.reduce((s, r) => s + (r.B ?? 0), 0)
  const singleChangePct = totalB > 0 ? ((totalA - totalB) / totalB) * 100 : null

  // ── Section 2: Multi-week comparison ───────────────────────────────────────
  const [multiMode, setMultiMode] = useState<'range' | 'custom'>('range')
  const [yearA, setYearA] = useState(today.getFullYear())
  const [yearB, setYearB] = useState(today.getFullYear() - 1)
  const [rangeStart, setRangeStart] = useState(1)
  const [rangeEnd, setRangeEnd]   = useState(isoWeekNum(today))
  const [customInput, setCustomInput] = useState('W01-W12')

  const activeWeeks = useMemo<number[]>(() => {
    if (multiMode === 'range') {
      const s = Math.max(1, Math.min(rangeStart, 53))
      const e = Math.max(s, Math.min(rangeEnd, 53))
      return Array.from({ length: e - s + 1 }, (_, i) => s + i)
    }
    return parseWeekSet(customInput)
  }, [multiMode, rangeStart, rangeEnd, customInput])

  const multiWeekData = useMemo<WeekRow[]>(() => {
    if (!channelObs || activeWeeks.length === 0) return []
    return buildMultiWeek(channelObs, yearA, yearB, activeWeeks)
  }, [channelObs, yearA, yearB, activeWeeks])

  const multiTotalA = multiWeekData.reduce((s, r) => s + r.A, 0)
  const multiTotalB = multiWeekData.reduce((s, r) => s + r.B, 0)
  const multiChangePct = multiTotalA > 0 ? ((multiTotalB - multiTotalA) / multiTotalA) * 100 : null

  // ── Section 3: Monthly forecast vs historical ───────────────────────────────
  const allHistoricalYears = useMemo(() =>
    [...new Set((monthly?.historical ?? []).map((h) => h.month.slice(0, 4)))].sort(),
    [monthly])
  const allForecastYears = useMemo(() =>
    [...new Set((monthly?.forecast ?? []).map((f) => f.month.slice(0, 4)))].sort(),
    [monthly])
  const allMonthlyYears = useMemo(() =>
    [...new Set([...allHistoricalYears, ...allForecastYears])].sort(),
    [allHistoricalYears, allForecastYears])

  const [monthYearA, setMonthYearA] = useState('')
  const [monthYearB, setMonthYearB] = useState('')

  useEffect(() => {
    if (allHistoricalYears.length && !monthYearA) setMonthYearA(allHistoricalYears[allHistoricalYears.length - 1])
  }, [allHistoricalYears])
  useEffect(() => {
    if (allForecastYears.length && !monthYearB) setMonthYearB(allForecastYears[0]!)
  }, [allForecastYears])

  const monthlyChartData = useMemo(() => {
    if (!monthly || !monthYearA || !monthYearB) return []
    const histMap = new Map(monthly.historical.map((h) => [h.month, h.total]))
    const fcstMap = new Map(monthly.forecast.map((f) => [f.month, f.total]))
    return MONTH_ABBR.map((name, i) => {
      const mm = String(i + 1).padStart(2, '0')
      const valA = histMap.get(`${monthYearA}-${mm}`) ?? null
      const valB = fcstMap.get(`${monthYearB}-${mm}`) ?? histMap.get(`${monthYearB}-${mm}`) ?? null
      return {
        month: name,
        A: valA != null ? Math.round(valA) : undefined,
        B: valB != null ? Math.round(valB) : undefined,
      }
    }).filter((r) => r.A !== undefined || r.B !== undefined)
  }, [monthly, monthYearA, monthYearB])

  if (!channels || channels.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <p className="text-slate-500 dark:text-slate-400">
          No channels available — upload data and train models first.
        </p>
      </div>
    )
  }

  const labelA = weekA || 'Week A'
  const labelB = weekB || 'Week B'

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Analysis</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Flexible week, multi-week, and monthly comparisons
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
          {/* ── SECTION 1: Single-Week Comparison ──────────────────────────── */}
          <Card className="p-5">
            <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200 mb-4">
              Single-Week Comparison — {channel}
            </h2>

            {/* Week pickers */}
            <div className="flex flex-wrap gap-x-6 gap-y-3 mb-4 items-center">
              <div className="flex items-center gap-2">
                <span className="inline-block w-3 h-3 rounded-sm flex-shrink-0" style={{ background: '#2563EB' }} />
                <label className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Week A</label>
                <select
                  value={parsedA?.year ?? today.getFullYear()}
                  onChange={(e) => setWeekA(`${e.target.value}-W${String(parsedA?.week ?? 1).padStart(2, '0')}`)}
                  className="rounded border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-sm text-slate-800 dark:text-slate-200 px-2 py-1"
                >
                  {[...new Set([String(parsedA?.year ?? today.getFullYear()), ...availableYears])].sort().reverse().map((y) => (
                    <option key={y} value={y}>{y}</option>
                  ))}
                </select>
                <select
                  value={parsedA?.week ?? 1}
                  onChange={(e) => setWeekA(`${parsedA?.year ?? today.getFullYear()}-W${String(e.target.value).padStart(2, '0')}`)}
                  className="rounded border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-sm text-slate-800 dark:text-slate-200 px-2 py-1"
                >
                  {WEEK_OPTIONS.map((w) => (
                    <option key={w} value={w}>W{String(w).padStart(2, '0')}</option>
                  ))}
                </select>
              </div>

              <div className="hidden sm:block w-px h-6 bg-slate-200 dark:bg-slate-700 self-center" />

              <div className="flex items-center gap-2">
                <span className="inline-block w-3 h-3 rounded-sm flex-shrink-0" style={{ background: '#94A3B8' }} />
                <label className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Week B</label>
                <select
                  value={parsedB?.year ?? today.getFullYear()}
                  onChange={(e) => setWeekB(`${e.target.value}-W${String(parsedB?.week ?? 1).padStart(2, '0')}`)}
                  className="rounded border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-sm text-slate-800 dark:text-slate-200 px-2 py-1"
                >
                  {[...new Set([String(parsedB?.year ?? today.getFullYear()), ...availableYears])].sort().reverse().map((y) => (
                    <option key={y} value={y}>{y}</option>
                  ))}
                </select>
                <select
                  value={parsedB?.week ?? 1}
                  onChange={(e) => setWeekB(`${parsedB?.year ?? today.getFullYear()}-W${String(e.target.value).padStart(2, '0')}`)}
                  className="rounded border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-sm text-slate-800 dark:text-slate-200 px-2 py-1"
                >
                  {WEEK_OPTIONS.map((w) => (
                    <option key={w} value={w}>W{String(w).padStart(2, '0')}</option>
                  ))}
                </select>
              </div>
            </div>

            {/* Summary chips */}
            <div className="flex flex-wrap gap-4 mb-4">
              <StatChip label={labelA} value={fmt(totalA)} />
              <StatChip label={labelB} value={fmt(totalB)} />
              {singleChangePct !== null && (
                <span className={changeCls(singleChangePct) + ' text-sm'}>
                  {fmtPct(singleChangePct)} vs Week B
                </span>
              )}
            </div>

            {/* Daily chart */}
            {channelObs ? (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={dailyData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                  <XAxis dataKey="day" tick={{ fontSize: 11 }} />
                  <YAxis tickFormatter={fmt} width={72} tick={{ fontSize: 11 }} />
                  <Tooltip
                    formatter={(v: number, name: string) => [fmt(v), name === 'A' ? labelA : labelB]}
                  />
                  <Legend formatter={(v) => (v === 'A' ? labelA : labelB)} />
                  <Bar dataKey="A" fill="#2563EB" radius={[3, 3, 0, 0]} />
                  <Bar dataKey="B" fill="#94A3B8" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-slate-400 dark:text-slate-500">No observation data available.</p>
            )}
          </Card>

          {/* ── SECTION 2: Multi-Week Comparison ───────────────────────────── */}
          <Card className="p-5">
            <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200 mb-4">
              Multi-Week Comparison — {channel}
            </h2>

            {/* Controls row */}
            <div className="flex flex-wrap gap-x-6 gap-y-3 mb-5 items-end">

              {/* Year selectors */}
              <div className="flex items-center gap-2">
                <span className="inline-block w-3 h-3 rounded-sm flex-shrink-0" style={{ background: '#2563EB' }} />
                <label className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                  Year A
                </label>
                <select
                  value={yearA}
                  onChange={(e) => setYearA(Number(e.target.value))}
                  className="rounded border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-sm text-slate-800 dark:text-slate-200 px-2 py-1"
                >
                  {[...new Set([String(yearA), ...availableYears])].sort().reverse().map((y) => (
                    <option key={y} value={y}>{y}</option>
                  ))}
                </select>
              </div>

              <div className="flex items-center gap-2">
                <span className="inline-block w-3 h-3 rounded-sm flex-shrink-0" style={{ background: '#94A3B8' }} />
                <label className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                  Year B
                </label>
                <select
                  value={yearB}
                  onChange={(e) => setYearB(Number(e.target.value))}
                  className="rounded border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-sm text-slate-800 dark:text-slate-200 px-2 py-1"
                >
                  {[...new Set([String(yearB), ...availableYears])].sort().reverse().map((y) => (
                    <option key={y} value={y}>{y}</option>
                  ))}
                </select>
              </div>

              {/* Divider */}
              <div className="hidden sm:block w-px h-6 bg-slate-200 dark:bg-slate-700 self-center" />

              {/* Mode toggle */}
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                  Mode
                </span>
                <div className="flex gap-1">
                  <ModeTab active={multiMode === 'range'}  label="Range"  onClick={() => setMultiMode('range')} />
                  <ModeTab active={multiMode === 'custom'} label="Custom" onClick={() => setMultiMode('custom')} />
                </div>
              </div>

              {/* Range inputs */}
              {multiMode === 'range' && (
                <div className="flex items-center gap-2">
                  <label className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                    Weeks
                  </label>
                  <select
                    value={rangeStart}
                    onChange={(e) => setRangeStart(Number(e.target.value))}
                    className="rounded border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-sm text-slate-800 dark:text-slate-200 px-2 py-1"
                  >
                    {WEEK_OPTIONS.map((w) => (
                      <option key={w} value={w}>W{String(w).padStart(2, '0')}</option>
                    ))}
                  </select>
                  <span className="text-slate-400 text-sm">→</span>
                  <select
                    value={rangeEnd}
                    onChange={(e) => setRangeEnd(Number(e.target.value))}
                    className="rounded border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-sm text-slate-800 dark:text-slate-200 px-2 py-1"
                  >
                    {WEEK_OPTIONS.map((w) => (
                      <option key={w} value={w}>W{String(w).padStart(2, '0')}</option>
                    ))}
                  </select>
                  <span className="text-xs text-slate-400">
                    ({activeWeeks.length} week{activeWeeks.length !== 1 ? 's' : ''})
                  </span>
                </div>
              )}

              {/* Custom input */}
              {multiMode === 'custom' && (
                <div className="flex items-center gap-2 flex-1 min-w-0">
                  <label className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide whitespace-nowrap">
                    Weeks
                  </label>
                  <input
                    type="text"
                    value={customInput}
                    onChange={(e) => setCustomInput(e.target.value)}
                    placeholder="e.g. W01, W03-W08, W10"
                    className="flex-1 min-w-0 rounded border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-sm text-slate-800 dark:text-slate-200 px-2 py-1"
                  />
                  <span className="text-xs text-slate-400 whitespace-nowrap">
                    {activeWeeks.length} week{activeWeeks.length !== 1 ? 's' : ''}
                  </span>
                </div>
              )}
            </div>

            {/* Summary chips */}
            {multiWeekData.length > 0 && (
              <div className="flex flex-wrap gap-4 mb-4">
                <StatChip label={`Total ${yearA}`} value={fmt(multiTotalA)} />
                <StatChip label={`Total ${yearB}`} value={fmt(multiTotalB)} />
                {multiChangePct !== null && (
                  <span className={changeCls(multiChangePct) + ' text-sm'}>
                    {fmtPct(multiChangePct)} vs {yearA}
                  </span>
                )}
              </div>
            )}

            {/* Multi-week chart */}
            {multiWeekData.length === 0 ? (
              <p className="text-sm text-slate-400 dark:text-slate-500">
                {channelObs ? 'No weeks selected or data unavailable.' : 'No observation data available.'}
              </p>
            ) : (
              <ResponsiveContainer
                width="100%"
                height={Math.max(260, multiWeekData.length > 20 ? 320 : 260)}
              >
                <BarChart
                  data={multiWeekData}
                  margin={{ top: 4, right: 16, left: 0, bottom: multiWeekData.length > 12 ? 40 : 8 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                  <XAxis
                    dataKey="week"
                    tick={{ fontSize: 11 }}
                    angle={multiWeekData.length > 12 ? -45 : 0}
                    textAnchor={multiWeekData.length > 12 ? 'end' : 'middle'}
                    interval={0}
                  />
                  <YAxis tickFormatter={fmt} width={72} tick={{ fontSize: 11 }} />
                  <Tooltip
                    formatter={(v: number, name: string) => [fmt(v), name === 'A' ? String(yearA) : String(yearB)]}
                  />
                  <Legend formatter={(v) => (v === 'A' ? String(yearA) : String(yearB))} />
                  <Bar dataKey="A" radius={[3, 3, 0, 0]}>
                    {multiWeekData.map((_, i) => (
                      <Cell key={i} fill="#2563EB" />
                    ))}
                  </Bar>
                  <Bar dataKey="B" radius={[3, 3, 0, 0]}>
                    {multiWeekData.map((_, i) => (
                      <Cell key={i} fill="#94A3B8" />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}

            {/* Detail table */}
            {multiWeekData.length > 0 && (
              <div className="overflow-x-auto mt-5">
                <table className="min-w-full text-sm text-slate-700 dark:text-slate-300">
                  <thead>
                    <tr className="border-b border-slate-200 dark:border-slate-700 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                      <th className="pb-2 pr-4 text-left">Week</th>
                      <th className="pb-2 px-4 text-right">{yearA}</th>
                      <th className="pb-2 px-4 text-right">{yearB}</th>
                      <th className="pb-2 pl-4 text-right">Change</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {multiWeekData.map((row) => {
                      const chg = row.A > 0 ? ((row.B - row.A) / row.A) * 100 : null
                      return (
                        <tr key={row.week} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                          <td className="py-1.5 pr-4 font-medium tabular-nums">{row.week}</td>
                          <td className="py-1.5 px-4 text-right tabular-nums">{fmt(row.A)}</td>
                          <td className="py-1.5 px-4 text-right tabular-nums">{fmt(row.B)}</td>
                          <td className={`py-1.5 pl-4 text-right tabular-nums ${changeCls(chg)}`}>
                            {chg === null ? '—' : fmtPct(chg)}
                          </td>
                        </tr>
                      )
                    })}
                    {/* Totals row */}
                    <tr className="border-t-2 border-slate-300 dark:border-slate-600 font-semibold">
                      <td className="py-2 pr-4">Total</td>
                      <td className="py-2 px-4 text-right tabular-nums">{fmt(multiTotalA)}</td>
                      <td className="py-2 px-4 text-right tabular-nums">{fmt(multiTotalB)}</td>
                      <td className={`py-2 pl-4 text-right tabular-nums ${changeCls(multiChangePct)}`}>
                        {multiChangePct === null ? '—' : fmtPct(multiChangePct)}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            )}
          </Card>

          {/* ── SECTION 3: Monthly Forecast vs Historical ───────────────────── */}
          {(monthly || monthlyChartData.length > 0) && (
            <Card className="p-5">
              <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200 mb-4">
                Monthly Comparison — {channel}
              </h2>

              {/* Year selectors */}
              <div className="flex flex-wrap gap-x-6 gap-y-3 mb-5 items-end">
                <div className="flex items-center gap-2">
                  <span className="inline-block w-3 h-3 rounded-sm flex-shrink-0" style={{ background: '#2563EB' }} />
                  <label className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Year A</label>
                  <select
                    value={monthYearA}
                    onChange={(e) => setMonthYearA(e.target.value)}
                    className="rounded border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-sm text-slate-800 dark:text-slate-200 px-2 py-1"
                  >
                    {allHistoricalYears.map((y) => <option key={y} value={y}>{y}</option>)}
                  </select>
                </div>
                <div className="flex items-center gap-2">
                  <span className="inline-block w-3 h-3 rounded-sm flex-shrink-0" style={{ background: '#F59E0B' }} />
                  <label className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Year B</label>
                  <select
                    value={monthYearB}
                    onChange={(e) => setMonthYearB(e.target.value)}
                    className="rounded border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-sm text-slate-800 dark:text-slate-200 px-2 py-1"
                  >
                    {allMonthlyYears.map((y) => <option key={y} value={y}>{y}</option>)}
                  </select>
                </div>
              </div>

              {monthlyChartData.length > 0 ? (
                <>
                  <ResponsiveContainer width="100%" height={280}>
                    <BarChart data={monthlyChartData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                      <XAxis dataKey="month" tick={{ fontSize: 11 }} interval={0} />
                      <YAxis tickFormatter={fmt} width={72} tick={{ fontSize: 11 }} />
                      <Tooltip formatter={(v: number) => fmt(v)} />
                      <Legend formatter={(v) => (v === 'A' ? monthYearA : monthYearB)} />
                      <Bar dataKey="A" fill="#2563EB" radius={[3, 3, 0, 0]} />
                      <Bar dataKey="B" fill="#F59E0B" radius={[3, 3, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>

                  <div className="overflow-x-auto mt-5">
                    <table className="min-w-full text-sm text-slate-700 dark:text-slate-300">
                      <thead>
                        <tr className="border-b border-slate-200 dark:border-slate-700 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">
                          <th className="pb-2 pr-4 text-left">Month</th>
                          <th className="pb-2 px-4 text-right">{monthYearA}</th>
                          <th className="pb-2 px-4 text-right">{monthYearB}</th>
                          <th className="pb-2 pl-4 text-right">Change</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                        {monthlyChartData.map((row) => {
                          const chg =
                            row.A && row.A > 0 && row.B != null
                              ? ((row.B - row.A) / row.A) * 100
                              : null
                          return (
                            <tr key={row.month} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                              <td className="py-1.5 pr-4 font-medium">{row.month}</td>
                              <td className="py-1.5 px-4 text-right tabular-nums">{row.A != null ? fmt(row.A) : '—'}</td>
                              <td className="py-1.5 px-4 text-right tabular-nums">{row.B != null ? fmt(row.B) : '—'}</td>
                              <td className={`py-1.5 pl-4 text-right tabular-nums ${changeCls(chg)}`}>
                                {chg === null ? '—' : fmtPct(chg)}
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                </>
              ) : (
                <p className="text-sm text-slate-400 dark:text-slate-500">No data for the selected years.</p>
              )}
            </Card>
          )}

          {/* ── SECTION 4: Seasonality ─────────────────────────────────────── */}
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

          {/* ── SECTION 5: Intraday Pattern (hourly data only) ──────────────── */}
          {isHourly && hourlyPattern && hourlyPattern.length > 0 && (
            <Card className="p-5">
              <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200 mb-2">
                Intraday Pattern — {channel}
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
                Average volume per hour across all historical days
              </p>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart
                  data={hourlyPattern.map((p) => ({ hour: fmtHour(p.hour), vol: p.avg_volume }))}
                  margin={{ top: 4, right: 16, left: 0, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                  <XAxis dataKey="hour" tick={{ fontSize: 10 }} interval={1} />
                  <YAxis tickFormatter={fmt} width={60} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(v: number) => [fmt(v), 'Avg volume']} />
                  <Bar dataKey="vol" fill="#2563EB" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </Card>
          )}

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
