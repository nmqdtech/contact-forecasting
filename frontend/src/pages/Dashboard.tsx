import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, CheckCircle, Database, Trash2, XCircle } from 'lucide-react'
import { useState } from 'react'
import { listDatasets, resetAllData, uploadFiles } from '../api/uploads'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import FileUploader from '../components/ui/FileUploader'
import MetricCard from '../components/ui/MetricCard'
import ProgressBar from '../components/ui/ProgressBar'
import { useChannels } from '../hooks/useChannels'
import { useSummary } from '../hooks/useForecasts'
import { useStartTraining, useTrainingStatus } from '../hooks/useTraining'
import { useAppStore } from '../store/useAppStore'
import type { DatasetOut } from '../types'

const statusVariant = (s: string) => {
  if (s === 'completed') return 'success'
  if (s === 'failed') return 'error'
  if (s === 'running') return 'info'
  return 'pending'
}

export default function Dashboard() {
  const qc = useQueryClient()
  const { activeDatasetId, activeJobId, setActiveDatasetId, setActiveJobId, activeProjectId } = useAppStore()

  const [selectedChannels, setSelectedChannels] = useState<string[]>([])
  const [monthsAhead, setMonthsAhead] = useState(15)
  const [uploadInfo, setUploadInfo] = useState<DatasetOut | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [confirmReset, setConfirmReset] = useState(false)

  const { data: channels } = useChannels()
  const { data: summary } = useSummary()

  // Active dataset info from API
  const { data: datasets } = useQuery({
    queryKey: ['datasets'],
    queryFn: listDatasets,
  })
  const activeDataset = datasets?.find((d) => d.is_active)

  // Training
  const trainMutation = useStartTraining()
  const { data: jobStatus } = useTrainingStatus(activeJobId)

  // File upload mutation
  const uploadMutation = useMutation({
    mutationFn: (files: File[]) => uploadFiles(files, { projectId: activeProjectId }),
    onSuccess: (data) => {
      setUploadInfo(data)
      setUploadError(null)
      setActiveDatasetId(data.dataset_id)
      setSelectedChannels(data.channels)
      qc.invalidateQueries({ queryKey: ['channels'] })
      qc.invalidateQueries({ queryKey: ['datasets'] })
      qc.invalidateQueries({ queryKey: ['summary'] })
    },
    onError: (err: unknown) => {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setUploadError(msg ?? 'Upload failed')
    },
  })

  // Reset mutation
  const resetMutation = useMutation({
    mutationFn: resetAllData,
    onSuccess: () => {
      setUploadInfo(null)
      setUploadError(null)
      setSelectedChannels([])
      setActiveDatasetId(null)
      setActiveJobId(null)
      setConfirmReset(false)
      qc.invalidateQueries()
    },
  })

  const handleTrain = () => {
    const datasetId = uploadInfo?.dataset_id ?? activeDataset?.dataset_id ?? activeDatasetId
    if (!datasetId || selectedChannels.length === 0) return
    setActiveJobId(null)
    trainMutation.mutate({ dataset_id: datasetId, channels: selectedChannels, months_ahead: monthsAhead })
  }

  const toggleChannel = (ch: string) =>
    setSelectedChannels((prev) =>
      prev.includes(ch) ? prev.filter((c) => c !== ch) : [...prev, ch]
    )

  const isTrainingActive =
    jobStatus?.status === 'pending' || jobStatus?.status === 'running'

  // Determine which channels to show for selection
  const availableChannels =
    uploadInfo?.channels ?? channels?.map((c) => c.name) ?? []

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Dashboard</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Upload historical data, train models, and view forecasts
          </p>
        </div>

        {/* Reset button */}
        {!confirmReset ? (
          <button
            onClick={() => setConfirmReset(true)}
            className="flex items-center gap-2 px-3 py-1.5 text-sm text-red-600 dark:text-red-400 border border-red-200 dark:border-red-800 rounded-lg hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors"
          >
            <Trash2 className="w-4 h-4" />
            Reset all data
          </button>
        ) : (
          <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-lg">
            <AlertTriangle className="w-4 h-4 text-red-600 dark:text-red-400 shrink-0" />
            <span className="text-sm text-red-700 dark:text-red-300">Delete all datasets, models & forecasts?</span>
            <button
              onClick={() => resetMutation.mutate()}
              disabled={resetMutation.isPending}
              className="px-3 py-1 text-sm font-medium bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50 transition-colors"
            >
              {resetMutation.isPending ? 'Deleting…' : 'Yes, reset'}
            </button>
            <button
              onClick={() => setConfirmReset(false)}
              className="px-3 py-1 text-sm border border-slate-300 dark:border-slate-600 rounded hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors text-slate-700 dark:text-slate-300"
            >
              Cancel
            </button>
          </div>
        )}
      </div>

      {/* Upload section */}
      <Card className="p-6">
        <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200 mb-4">
          1 — Upload Historical Data
        </h2>
        <FileUploader
          onFiles={(files) => uploadMutation.mutate(files)}
          loading={uploadMutation.isPending}
        />
        {uploadError && (
          <p className="mt-3 text-sm text-red-600 dark:text-red-400 flex items-center gap-2">
            <XCircle className="w-4 h-4" /> {uploadError}
          </p>
        )}
        {uploadInfo && (
          <div className="mt-4 flex flex-wrap gap-3 text-sm text-slate-700 dark:text-slate-300">
            <span className="flex items-center gap-1.5">
              <CheckCircle className="w-4 h-4 text-emerald-500" />
              <strong>{uploadInfo.filename}</strong>
            </span>
            <span>{uploadInfo.row_count.toLocaleString()} rows</span>
            <span>
              {uploadInfo.date_min} → {uploadInfo.date_max}
            </span>
            <span>Channels: {uploadInfo.channels.join(', ')}</span>
          </div>
        )}
        {!uploadInfo && activeDataset && (
          <div className="mt-3 flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
            <Database className="w-4 h-4" />
            Active dataset: <strong>{activeDataset.filename}</strong> ({activeDataset.row_count?.toLocaleString()} rows)
          </div>
        )}
      </Card>

      {/* Training section */}
      {availableChannels.length > 0 && (
        <Card className="p-6">
          <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200 mb-4">
            2 — Configure & Train
          </h2>

          <div className="space-y-4">
            {/* Channel checkboxes */}
            <div>
              <p className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                Select channels to train:
              </p>
              <div className="flex flex-wrap gap-2">
                {availableChannels.map((ch) => (
                  <label
                    key={ch}
                    className="flex items-center gap-2 cursor-pointer select-none text-sm text-slate-700 dark:text-slate-300"
                  >
                    <input
                      type="checkbox"
                      checked={selectedChannels.includes(ch)}
                      onChange={() => toggleChannel(ch)}
                      className="rounded border-slate-300 dark:border-slate-600 text-blue-600"
                    />
                    {ch}
                  </label>
                ))}
              </div>
            </div>

            {/* Months ahead slider */}
            <div>
              <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
                Forecast horizon: <strong>{monthsAhead} months</strong>
              </label>
              <input
                type="range"
                min={3}
                max={24}
                value={monthsAhead}
                onChange={(e) => setMonthsAhead(Number(e.target.value))}
                className="block w-full mt-2 accent-blue-600"
              />
            </div>

            <Button
              onClick={handleTrain}
              loading={trainMutation.isPending || isTrainingActive}
              disabled={selectedChannels.length === 0}
            >
              {isTrainingActive ? 'Training…' : 'Train Models'}
            </Button>
          </div>
        </Card>
      )}

      {/* Training progress */}
      {jobStatus && (
        <Card className="p-6">
          <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200 mb-4">
            3 — Training Progress
          </h2>
          <ProgressBar progress={jobStatus.progress} label="Overall" />
          <div className="mt-4 space-y-2">
            {jobStatus.results.map((r) => (
              <div key={r.channel} className="flex items-center justify-between">
                <span className="text-sm text-slate-700 dark:text-slate-300">{r.channel}</span>
                <div className="flex items-center gap-2">
                  {r.aic != null && (
                    <span className="text-xs text-slate-500">AIC {r.aic.toFixed(0)}</span>
                  )}
                  {r.backtest_mape != null && (
                    <span className="text-xs text-slate-500">
                      MAPE {r.backtest_mape.toFixed(1)}%
                    </span>
                  )}
                  <Badge label={r.status} variant={statusVariant(r.status) as 'success' | 'error' | 'info' | 'pending'} />
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Channel KPI cards */}
      {summary && summary.length > 0 && (
        <div>
          <h2 className="text-base font-semibold text-slate-800 dark:text-slate-200 mb-4">
            Channel Overview
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
            {summary.map((row) => (
              <MetricCard
                key={row.channel}
                label={row.channel}
                value={row.forecast_avg_daily.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                sub={`avg daily · ${row.change_pct >= 0 ? '+' : ''}${row.change_pct.toFixed(1)}% vs hist`}
                accentColor={row.change_pct >= 0 ? '#059669' : '#EF4444'}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
