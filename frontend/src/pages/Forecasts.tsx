import { useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, Upload, X } from 'lucide-react'
import {
  Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import Card from '../components/ui/Card'
import BacktestChart from '../components/charts/BacktestChart'
import ForecastChart from '../components/charts/ForecastChart'
import MonthlyChart from '../components/charts/MonthlyChart'
import { useChannels, useChannelData, useChannelHourly } from '../hooks/useChannels'
import { useBacktest, useForecast, useMonthlyForecast } from '../hooks/useForecasts'
import { uploadFiles } from '../api/uploads'
import { useAppStore } from '../store/useAppStore'

const fmt = (n: number) => n.toLocaleString(undefined, { maximumFractionDigits: 0 })
const fmtHour = (h: number) => h === 0 ? '12AM' : h < 12 ? `${h}AM` : h === 12 ? '12PM' : `${h - 12}PM`

export default function Forecasts() {
  const qc = useQueryClient()
  const { data: channels } = useChannels()
  const [activeChannel, setActiveChannel] = useState<string | null>(null)
  const [backtestOpen, setBacktestOpen] = useState(false)
  const [bannerDismissed, setBannerDismissed] = useState(false)
  const [actualsError, setActualsError] = useState<string | null>(null)
  const actualsInputRef = useRef<HTMLInputElement>(null)

  const chartSettings = useAppStore((s) => s.chartSettings)
  const setChartSettings = useAppStore((s) => s.setChartSettings)
  const activeProjectId = useAppStore((s) => s.activeProjectId)

  const channel = activeChannel ?? channels?.[0]?.name ?? null
  const isHourly = channels?.find((c) => c.name === channel)?.is_hourly ?? false

  const { data: forecast, isLoading: fcLoading } = useForecast(channel)
  const { data: monthly, isLoading: moLoading } = useMonthlyForecast(channel)
  const { data: backtest } = useBacktest(channel)
  const { data: channelObs } = useChannelData(channel)
  const { data: hourlyPattern } = useChannelHourly(isHourly ? channel : null)

  // Gap detection
  const todayStr = new Date().toISOString().slice(0, 10)
  const yesterdayStr = new Date(Date.now() - 86400000).toISOString().slice(0, 10)
  const lastHistDate = channelObs
    ? channelObs.filter((d) => !d.is_actuals).slice(-1)[0]?.date ?? null
    : null
  const hasGap = !!lastHistDate && lastHistDate < yesterdayStr
  const hasActuals = channelObs?.some((d) => d.is_actuals) ?? false

  const actualsMut = useMutation({
    mutationFn: (files: File[]) =>
      uploadFiles(files, { projectId: activeProjectId, isActuals: true }),
    onSuccess: () => {
      setActualsError(null)
      setBannerDismissed(true)
      qc.invalidateQueries({ queryKey: ['channel-data'] })
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setActualsError(msg ?? 'Upload failed')
    },
  })

  if (!channels || channels.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <p className="text-slate-500 dark:text-slate-400">
          No channels available — upload data and train models first.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Forecasts</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Daily and monthly contact volume projections
        </p>
      </div>

      {/* Channel tabs */}
      <div className="flex gap-2 flex-wrap">
        {channels.map((ch) => (
          <button
            key={ch.name}
            onClick={() => {
              setActiveChannel(ch.name)
              setBacktestOpen(false)
            }}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              (channel === ch.name)
                ? 'bg-blue-600 text-white'
                : 'bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700'
            }`}
          >
            {ch.name}
          </button>
        ))}
      </div>

      {/* Gap banner */}
      {channel && hasGap && !bannerDismissed && (
        <div className="flex flex-wrap items-start gap-3 p-4 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 text-sm">
          <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <p className="text-amber-800 dark:text-amber-300 font-medium">
              Historical data ends on {lastHistDate} — {Math.round((new Date(yesterdayStr).getTime() - new Date(lastHistDate!).getTime()) / 86400000)} day gap before yesterday.
            </p>
            <p className="text-amber-700 dark:text-amber-400 mt-0.5">
              {hasActuals
                ? 'Actuals uploaded — shown in green on the chart.'
                : 'Gap forecast shown as a dashed line. You can optionally upload actuals for a more accurate view.'}
            </p>
            {!hasActuals && (
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <input
                  ref={actualsInputRef}
                  type="file"
                  accept=".xlsx,.xls,.csv"
                  className="hidden"
                  onChange={(e) => {
                    const files = Array.from(e.target.files ?? [])
                    if (files.length) actualsMut.mutate(files)
                    e.target.value = ''
                  }}
                />
                <button
                  onClick={() => actualsInputRef.current?.click()}
                  disabled={actualsMut.isPending}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white text-xs font-medium rounded transition-colors"
                >
                  <Upload className="w-3.5 h-3.5" />
                  {actualsMut.isPending ? 'Uploading…' : 'Upload actuals'}
                </button>
                {actualsError && (
                  <span className="text-xs text-red-600 dark:text-red-400">{actualsError}</span>
                )}
              </div>
            )}
          </div>
          <button
            onClick={() => setBannerDismissed(true)}
            className="text-amber-500 hover:text-amber-700 dark:hover:text-amber-300 flex-shrink-0"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {channel && (
        <>
          {/* Daily forecast chart */}
          <Card className="p-5">
            <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
              <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200">
                Daily Forecast — {channel}
              </h2>
            </div>

            {fcLoading ? (
              <div className="h-96 flex items-center justify-center text-slate-400">Loading…</div>
            ) : forecast?.data.length ? (
              <ForecastChart
                data={forecast.data}
                historical={channelObs}
              />
            ) : (
              <div className="h-40 flex items-center justify-center text-slate-400 text-sm">
                No forecast data — train a model first.
              </div>
            )}

            {/* Chart settings panel */}
            <details className="mt-4">
              <summary className="text-xs font-medium text-slate-500 dark:text-slate-400 cursor-pointer select-none">
                Chart Settings
              </summary>
              <div className="mt-3 flex flex-wrap gap-4 text-xs text-slate-700 dark:text-slate-300">
                <label className="flex items-center gap-2">
                  Historical color
                  <input
                    type="color"
                    value={chartSettings.historicalColor}
                    onChange={(e) => setChartSettings({ historicalColor: e.target.value })}
                    className="h-6 w-8 cursor-pointer rounded border border-slate-200 dark:border-slate-600"
                  />
                </label>
                <label className="flex items-center gap-2">
                  Forecast color
                  <input
                    type="color"
                    value={chartSettings.forecastColor}
                    onChange={(e) => setChartSettings({ forecastColor: e.target.value })}
                    className="h-6 w-8 cursor-pointer rounded border border-slate-200 dark:border-slate-600"
                  />
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={chartSettings.showDataLabels}
                    onChange={(e) => setChartSettings({ showDataLabels: e.target.checked })}
                    className="rounded"
                  />
                  Data labels
                </label>
                <label className="flex items-center gap-2">
                  Y-axis scale
                  <select
                    value={chartSettings.yAxisScale}
                    onChange={(e) =>
                      setChartSettings({ yAxisScale: e.target.value as 'auto' | 'log' })
                    }
                    className="rounded border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 px-2 py-0.5 text-xs"
                  >
                    <option value="auto">Auto</option>
                    <option value="log">Log</option>
                  </select>
                </label>
              </div>
            </details>
          </Card>

          {/* Monthly chart */}
          <Card className="p-5">
            <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200 mb-4">
              Monthly Overview — {channel}
            </h2>
            {moLoading ? (
              <div className="h-72 flex items-center justify-center text-slate-400">Loading…</div>
            ) : monthly ? (
              <MonthlyChart historical={monthly.historical} forecast={monthly.forecast} />
            ) : (
              <div className="h-40 flex items-center justify-center text-slate-400 text-sm">
                No data available.
              </div>
            )}
          </Card>

          {/* Intraday pattern (hourly data only) */}
          {isHourly && hourlyPattern && hourlyPattern.length > 0 && (
            <Card className="p-5">
              <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200 mb-4">
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

          {/* Backtest expander */}
          {backtest && (
            <Card>
              <button
                onClick={() => setBacktestOpen((o) => !o)}
                className="w-full flex items-center justify-between px-5 py-4 text-left"
              >
                <span className="text-base font-semibold text-slate-800 dark:text-slate-200">
                  Backtest Results
                </span>
                <span className="text-slate-400 dark:text-slate-500 text-sm">
                  MAPE {backtest.metrics.mape.toFixed(1)}% · {backtestOpen ? '▲' : '▼'}
                </span>
              </button>
              {backtestOpen && (
                <div className="px-5 pb-5">
                  <div className="flex flex-wrap gap-4 mb-4 text-sm text-slate-600 dark:text-slate-400">
                    <span>MAE: <strong>{backtest.metrics.mae.toFixed(0)}</strong></span>
                    <span>RMSE: <strong>{backtest.metrics.rmse.toFixed(0)}</strong></span>
                    <span>Holdout: <strong>{backtest.metrics.holdout_days} days</strong></span>
                  </div>
                  <BacktestChart data={backtest.data} mape={backtest.metrics.mape} />
                </div>
              )}
            </Card>
          )}
        </>
      )}
    </div>
  )
}
