import { Download, FileSpreadsheet } from 'lucide-react'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import { exportForecastsUrl, exportSummaryUrl } from '../api/forecasts'
import { useSummary } from '../hooks/useForecasts'

export default function Export() {
  const { data: summary, isLoading } = useSummary()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Export</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Download forecast data and summary reports as Excel workbooks
        </p>
      </div>

      {/* Download cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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
          <a href={exportForecastsUrl()} download="forecasts.xlsx">
            <Button variant="primary" className="w-full justify-center">
              <Download className="w-4 h-4" /> Download forecasts.xlsx
            </Button>
          </a>
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
          <a href={exportSummaryUrl()} download="summary.xlsx">
            <Button variant="secondary" className="w-full justify-center">
              <Download className="w-4 h-4" /> Download summary.xlsx
            </Button>
          </a>
        </Card>
      </div>

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
                    <td className="py-2 pl-4 text-center">
                      {row.has_holidays ? '✓' : '—'}
                    </td>
                    <td className="py-2 pl-4 text-center">
                      {row.has_targets ? '✓' : '—'}
                    </td>
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
