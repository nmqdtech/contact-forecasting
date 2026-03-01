import type { ReactNode } from 'react'

interface MetricCardProps {
  label: string
  value: string | number
  sub?: string
  icon?: ReactNode
  accentColor?: string
}

export default function MetricCard({
  label,
  value,
  sub,
  icon,
  accentColor = '#2563EB',
}: MetricCardProps) {
  return (
    <div
      className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-4 shadow-sm flex items-start gap-3"
      style={{ borderLeft: `4px solid ${accentColor}` }}
    >
      {icon && <div className="mt-0.5 flex-shrink-0">{icon}</div>}
      <div className="min-w-0">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          {label}
        </p>
        <p className="text-2xl font-bold text-slate-900 dark:text-white mt-0.5 truncate">
          {value}
        </p>
        {sub && (
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{sub}</p>
        )}
      </div>
    </div>
  )
}
