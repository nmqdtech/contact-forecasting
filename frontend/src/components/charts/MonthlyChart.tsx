import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useAppStore } from '../../store/useAppStore'
import type { MonthlyForecastPoint, MonthlyPoint } from '../../types'

interface Props {
  historical: MonthlyPoint[]
  forecast: MonthlyForecastPoint[]
}

const fmt = (n: number) => n.toLocaleString(undefined, { maximumFractionDigits: 0 })

export default function MonthlyChart({ historical, forecast }: Props) {
  const theme = useAppStore((s) => s.theme)
  const gridColor = theme === 'dark' ? '#334155' : '#E2E8F0'
  const textColor = theme === 'dark' ? '#94A3B8' : '#64748B'
  const tooltipBg = theme === 'dark' ? '#1E293B' : '#FFFFFF'
  const tooltipBorder = theme === 'dark' ? '#334155' : '#E2E8F0'

  // Merge historical + forecast into one array keyed by month
  const allMonths = Array.from(
    new Set([...historical.map((h) => h.month), ...forecast.map((f) => f.month)])
  ).sort()

  const chartData = allMonths.map((month) => ({
    month,
    Historical: historical.find((h) => h.month === month)?.total ?? null,
    Forecast: forecast.find((f) => f.month === month)?.total ?? null,
  }))

  return (
    <ResponsiveContainer width="100%" height={360}>
      <BarChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
        <XAxis dataKey="month" tick={{ fontSize: 10, fill: textColor }} interval={1} />
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
        <Bar dataKey="Historical" fill="#2563EB" radius={[3, 3, 0, 0]} maxBarSize={32} />
        <Bar dataKey="Forecast" fill="#F59E0B" radius={[3, 3, 0, 0]} maxBarSize={32} />
      </BarChart>
    </ResponsiveContainer>
  )
}
