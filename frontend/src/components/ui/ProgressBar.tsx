interface ProgressBarProps {
  /** 0.0 – 1.0 */
  progress: number
  label?: string
  showPercent?: boolean
}

export default function ProgressBar({ progress, label, showPercent = true }: ProgressBarProps) {
  const pct = Math.min(100, Math.round(progress * 100))
  return (
    <div className="space-y-1">
      {(label || showPercent) && (
        <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400">
          {label && <span>{label}</span>}
          {showPercent && <span>{pct}%</span>}
        </div>
      )}
      <div className="h-2 rounded-full overflow-hidden bg-slate-200 dark:bg-slate-700">
        <div
          className="h-full rounded-full transition-all duration-500 bg-blue-600"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}
