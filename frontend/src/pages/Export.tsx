import { useState } from 'react'
import { Download, FileSpreadsheet, FileText, Zap } from 'lucide-react'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import { downloadForecasts, downloadIex, downloadReport, downloadSummary } from '../api/forecasts'
import { useChannels } from '../hooks/useChannels'
import { useSummary } from '../hooks/useForecasts'

export default function Export() {
  const { data: summary, isLoading } = useSummary()
  const { data: channels } = useChannels()
  const [downloading, setDownloading] = useState<string | null>(null)

  // IEX settings
  const [iexMinAht, setIexMinAht] = useState('')
  const [iexMaxAht, setIexMaxAht] = useState('')
  const [iexChannels, setIexChannels] = useState<string[]>([])

  async function handleDownload(key: string, fn: () => Promise<void>) {
    setDownloading(key)
    try {
      await fn()
    } finally {
      setDownloading(null)
    }
  }

  function handleIexChannelToggle(name: string) {
    setIexChannels((prev) =>
      prev.includes(name) ? prev.filter((c) => c !== name) : [...prev, name]
    )
  }

  function handleDownloadIex() {
    const min = iexMinAht !== '' ? parseFloat(iexMinAht) : null
    const max = iexMaxAht !== '' ? parseFloat(iexMaxAht) : null
    return handleDownload('iex', () =>
      downloadIex({
        channels: iexChannels.length > 0 ? iexChannels : undefined,
        min_aht: isNaN(min as number) ? null : min,
        max_aht: isNaN(max as number) ? null : max,
      })
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Export</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Download forecast data and reports
        </p>
      </div>

      {/* Standard downloads */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <Card className="p-5 flex flex-col gap-4">
          <div className="flex items-start gap-3">
            <FileSpreadsheet className="w-8 h-8 text-blue-500 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-slate-800 dark:text-slate-200">Forecasts Workbook</h3>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
                Daily forecast with confidence intervals — one sheet per channel
              </p>
            </div>
          </div>
          <Button
            variant="primary"
            className="w-full justify-center"
            loading={downloading === 'forecasts'}
            onClick={() => handleDownload('forecasts', downloadForecasts)}
          >
            <Download className="w-4 h-4" /> Download forecasts.xlsx
          </Button>
        </Card>

        <Card className="p-5 flex flex-col gap-4">
          <div className="flex items-start gap-3">
            <FileSpreadsheet className="w-8 h-8 text-emerald-500 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-slate-800 dark:text-slate-200">Summary Workbook</h3>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
                Cross-channel comparison of historical vs. forecast metrics
              </p>
            </div>
          </div>
          <Button
            variant="secondary"
            className="w-full justify-center"
            loading={downloading === 'summary'}
            onClick={() => handleDownload('summary', downloadSummary)}
          >
            <Download className="w-4 h-4" /> Download summary.xlsx
          </Button>
        </Card>

        <Card className="p-5 flex flex-col gap-4">
          <div className="flex items-start gap-3">
            <FileText className="w-8 h-8 text-violet-500 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-slate-800 dark:text-slate-200">PDF Report</h3>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
                Multi-page PDF with forecast charts and backtest results per channel
              </p>
            </div>
          </div>
          <Button
            variant="secondary"
            className="w-full justify-center"
            loading={downloading === 'report'}
            onClick={() => handleDownload('report', downloadReport)}
          >
            <Download className="w-4 h-4" /> Download forecast-report.pdf
          </Button>
        </Card>
      </div>

      {/* NICE IEX Export */}
      <Card className="p-5">
        <div className="flex items-start gap-3 mb-4">
          <Zap className="w-7 h-7 text-amber-500 flex-shrink-0 mt-0.5" />
          <div>
            <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200">
              NICE IEX Export
            </h2>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
              30-minute interval CSV for NICE IEX WFM.
              Skill · Date (MM/DD/YYYY) · Start Time · Contacts · AHT (seconds × 100).
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-5">
          {/* AHT Constraints */}
          <div className="space-y-3">
            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
              AHT Constraints (seconds)
            </p>
            <div className="flex items-center gap-3">
              <div className="flex-1">
                <label className="block text-xs text-slate-500 dark:text-slate-400 mb-1">Min AHT</label>
                <input
                  type="number"
                  min="1"
                  placeholder="e.g. 120"
                  value={iexMinAht}
                  onChange={(e) => setIexMinAht(e.target.value)}
                  className="w-full rounded border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-sm text-slate-800 dark:text-slate-200 px-3 py-1.5"
                />
              </div>
              <div className="flex-1">
                <label className="block text-xs text-slate-500 dark:text-slate-400 mb-1">Max AHT</label>
                <input
                  type="number"
                  min="1"
                  placeholder="e.g. 900"
                  value={iexMaxAht}
                  onChange={(e) => setIexMaxAht(e.target.value)}
                  className="w-full rounded border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-sm text-slate-800 dark:text-slate-200 px-3 py-1.5"
                />
              </div>
            </div>
          </div>

          {/* Channel filter */}
          {channels && channels.length > 0 && (
            <div className="space-y-3">
              <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                Channels <span className="text-slate-400 font-normal">(leave empty for all)</span>
              </p>
              <div className="flex flex-wrap gap-2">
                {channels.map((ch) => (
                  <button
                    key={ch.name}
                    onClick={() => handleIexChannelToggle(ch.name)}
                    className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                      iexChannels.includes(ch.name)
                        ? 'bg-amber-500 text-white'
                        : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600'
                    }`}
                  >
                    {ch.name}
                    {ch.has_aht && (
                      <span className="ml-1 opacity-75">AHT</span>
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        <Button
          variant="primary"
          className="justify-center"
          loading={downloading === 'iex'}
          onClick={handleDownloadIex}
        >
          <Download className="w-4 h-4" /> Download iex-forecast.csv
        </Button>
      </Card>

      {/* Summary table */}
      <Card className="p-5">
        <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200 mb-4">
          Summary Table
        </h2>
        {isLoading ? (
          <p className="text-slate-400 text-sm">Loading…</p>
        ) : !summary || summary.length === 0 ? (
          <p className="text-slate-400 text-sm">
            No data available — train models first.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm text-slate-700 dark:text-slate-300">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-700 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
                  <th className="pb-2 pr-4 text-left">Channel</th>
                  <th className="pb-2 px-4 text-right">Hist Avg/day</th>
                  <th className="pb-2 px-4 text-right">Fcst Avg/day</th>
                  <th className="pb-2 px-4 text-right">Change</th>
                  <th className="pb-2 px-4 text-right">Total 15m</th>
                  <th className="pb-2 px-4 text-left">Peak</th>
                  <th className="pb-2 px-4 text-left">Trough</th>
                  <th className="pb-2 pl-4 text-center">Holidays</th>
                  <th className="pb-2 pl-4 text-center">Targets</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {summary.map((row) => (
                  <tr key={row.channel} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                    <td className="py-2 pr-4 font-medium">{row.channel}</td>
                    <td className="py-2 px-4 text-right tabular-nums">
                      {row.hist_avg_daily.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </td>
                    <td className="py-2 px-4 text-right tabular-nums">
                      {row.forecast_avg_daily.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </td>
                    <td
                      className={`py-2 px-4 text-right tabular-nums font-semibold ${
                        row.change_pct >= 0
                          ? 'text-emerald-600 dark:text-emerald-400'
                          : 'text-red-600 dark:text-red-400'
                      }`}
                    >
                      {row.change_pct >= 0 ? '+' : ''}{row.change_pct.toFixed(1)}%
                    </td>
                    <td className="py-2 px-4 text-right tabular-nums">
                      {row.total_15m.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </td>
                    <td className="py-2 px-4">{row.peak_month}</td>
                    <td className="py-2 px-4">{row.trough_month}</td>
                    <td className="py-2 pl-4 text-center">{row.has_holidays ? '✓' : '—'}</td>
                    <td className="py-2 pl-4 text-center">{row.has_targets ? '✓' : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  )
}
