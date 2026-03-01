import { useState } from 'react'
import Card from '../components/ui/Card'
import SeasonalityChart from '../components/charts/SeasonalityChart'
import { useChannels } from '../hooks/useChannels'
import { useSeasonality } from '../hooks/useForecasts'

export default function Analysis() {
  const { data: channels } = useChannels()
  const [activeChannel, setActiveChannel] = useState<string | null>(null)

  const channel = activeChannel ?? channels?.[0]?.name ?? null
  const { data: seasonality, isLoading } = useSeasonality(channel)

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
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Seasonality Analysis</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Monthly and weekly contact volume patterns
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
        <Card className="p-5">
          <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200 mb-5">
            Seasonal Patterns — {channel}
          </h2>
          {isLoading ? (
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
    </div>
  )
}
