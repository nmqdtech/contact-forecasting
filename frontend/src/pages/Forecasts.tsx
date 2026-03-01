import { useState } from 'react'
import Card from '../components/ui/Card'
import BacktestChart from '../components/charts/BacktestChart'
import ForecastChart from '../components/charts/ForecastChart'
import MonthlyChart from '../components/charts/MonthlyChart'
import Badge from '../components/ui/Badge'
import { useChannels, useChannelData } from '../hooks/useChannels'
import { useBacktest, useForecast, useMonthlyForecast } from '../hooks/useForecasts'
import { useAppStore } from '../store/useAppStore'

function ModelBadge({ label, value }: { label: string; value: string }) {
  return (
    <span className="text-xs bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 px-2 py-1 rounded-md">
      <span className="text-slate-400 dark:text-slate-500">{label}:</span> {value}
    </span>
  )
}

export default function Forecasts() {
  const { data: channels } = useChannels()
  const [activeChannel, setActiveChannel] = useState<string | null>(null)
  const [backtestOpen, setBacktestOpen] = useState(false)
  const [showCI, setShowCI] = useState(true)
  const [showTrend, setShowTrend] = useState(false)

  const chartSettings = useAppStore((s) => s.chartSettings)
  const setChartSettings = useAppStore((s) => s.setChartSettings)

  const channel = activeChannel ?? channels?.[0]?.name ?? null

  const { data: forecast, isLoading: fcLoading } = useForecast(channel)
  const { data: monthly, isLoading: moLoading } = useMonthlyForecast(channel)
  const { data: backtest } = useBacktest(channel)
  const { data: channelObs } = useChannelData(channel)

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

      {channel && (
        <>
          {/* Model info */}
          {forecast?.model && (
            <div className="flex flex-wrap gap-2 items-center">
              {forecast.model.config && (
                <ModelBadge
                  label="Model"
                  value={`HW(${forecast.model.config[0]},${forecast.model.config[1]},damped=${forecast.model.config[2]})`}
                />
              )}
              {forecast.model.aic != null && (
                <ModelBadge label="AIC" value={forecast.model.aic.toFixed(1)} />
              )}
              {forecast.model.backtest_mape != null && (
                <ModelBadge label="MAPE" value={`${forecast.model.backtest_mape.toFixed(1)}%`} />
              )}
              {!forecast.model.config && (
                <Badge label="No model trained" variant="warning" />
              )}
            </div>
          )}

          {/* Daily forecast chart */}
          <Card className="p-5">
            <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
              <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200">
                Daily Forecast — {channel}
              </h2>

              {/* Toggle pills */}
              <div className="flex gap-2 flex-wrap">
                {[
                  { label: 'Confidence Interval', val: showCI, set: setShowCI },
                  { label: 'Trend Line', val: showTrend, set: setShowTrend },
                ].map(({ label, val, set }) => (
                  <button
                    key={label}
                    onClick={() => set(!val)}
                    className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                      val
                        ? 'bg-blue-600 text-white border-blue-600'
                        : 'border-slate-300 dark:border-slate-600 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            {fcLoading ? (
              <div className="h-96 flex items-center justify-center text-slate-400">Loading…</div>
            ) : forecast?.data.length ? (
              <ForecastChart
                data={forecast.data}
                historical={channelObs}
                showCI={showCI}
                showTrend={showTrend}
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
