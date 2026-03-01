import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useAppStore } from '../../store/useAppStore'
import type { BacktestPoint } from '../../types'

interface Props {
  data: BacktestPoint[]
  mape: number
}

const fmt = (n: number) => n.toLocaleString(undefined, { maximumFractionDigits: 0 })

export default function BacktestChart({ data, mape }: Props) {
  const theme = useAppStore((s) => s.theme)
  const gridColor = theme === 'dark' ? '#334155' : '#E2E8F0'
  const textColor = theme === 'dark' ? '#94A3B8' : '#64748B'
  const tooltipBg = theme === 'dark' ? '#1E293B' : '#FFFFFF'
  const tooltipBorder = theme === 'dark' ? '#334155' : '#E2E8F0'

  return (
    <div>
      <p className="text-xs text-slate-500 dark:text-slate-400 mb-3">
        MAPE: <strong className="text-slate-700 dark:text-slate-200">{mape.toFixed(1)}%</strong>
        {' · '}
        Holdout: <strong className="text-slate-700 dark:text-slate-200">{data.length} days</strong>
      </p>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10, fill: textColor }}
            tickFormatter={(v: string) => v.slice(5)}
            interval={13}
          />
          <YAxis tick={{ fontSize: 11, fill: textColor }} tickFormatter={fmt} width={72} />
          <Tooltip
            contentStyle={{
              background: tooltipBg,
              border: `1px solid ${tooltipBorder}`,
              borderRadius: 8,
              fontSize: 12,
            }}
            formatter={(value: number) => [fmt(value)]}
          />
          <Legend wrapperStyle={{ fontSize: 12, color: textColor }} />
          <Line
            dataKey="actual"
            stroke="#059669"
            strokeWidth={2}
            dot={false}
            name="Actual"
            isAnimationActive={false}
          />
          <Line
            dataKey="predicted"
            stroke="#F59E0B"
            strokeWidth={2}
            strokeDasharray="4 2"
            dot={false}
            name="Predicted"
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
