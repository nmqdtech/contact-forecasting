import { useState } from 'react'
import Card from '../components/ui/Card'
import BacktestChart from '../components/charts/BacktestChart'
import ForecastChart from '../components/charts/ForecastChart'
import MonthlyChart from '../components/charts/MonthlyChart'
import Badge from '../components/ui/Badge'
import { useChannels } from '../hooks/useChannels'
import { useBacktest, useForecast, useMonthlyForecast } from '../hooks/useForecasts'

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

  const channel = activeChannel ?? channels?.[0]?.name ?? null

  const { data: forecast, isLoading: fcLoading } = useForecast(channel)
  const { data: monthly, isLoading: moLoading } = useMonthlyForecast(channel)
  const { data: backtest } = useBacktest(channel)

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
            <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200 mb-4">
              Daily Forecast — {channel}
            </h2>
            {fcLoading ? (
              <div className="h-96 flex items-center justify-center text-slate-400">Loading…</div>
            ) : forecast?.data.length ? (
              <ForecastChart data={forecast.data} />
            ) : (
              <div className="h-40 flex items-center justify-center text-slate-400 text-sm">
                No forecast data — train a model first.
              </div>
            )}
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
