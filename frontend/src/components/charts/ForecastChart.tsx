import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useAppStore } from '../../store/useAppStore'
import type { ForecastPoint } from '../../types'

interface Props {
  data: ForecastPoint[]
}

const fmt = (n: number) => n.toLocaleString(undefined, { maximumFractionDigits: 0 })

export default function ForecastChart({ data }: Props) {
  const theme = useAppStore((s) => s.theme)
  const gridColor = theme === 'dark' ? '#334155' : '#E2E8F0'
  const textColor = theme === 'dark' ? '#94A3B8' : '#64748B'
  const tooltipBg = theme === 'dark' ? '#1E293B' : '#FFFFFF'
  const tooltipBorder = theme === 'dark' ? '#334155' : '#E2E8F0'

  // Build chart data: split yhat_lower as base + ci_band as height of the ribbon
  const chartData = data.map((d) => ({
    date: d.date,
    yhat: d.yhat,
    lower: d.yhat_lower,
    ci_band: Math.max(0, d.yhat_upper - d.yhat_lower),
  }))

  return (
    <ResponsiveContainer width="100%" height={420}>
      <ComposedChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 11, fill: textColor }}
          tickFormatter={(v: string) => v.slice(0, 7)}
          interval={29}
        />
        <YAxis
          tick={{ fontSize: 11, fill: textColor }}
          tickFormatter={fmt}
          width={72}
        />
        <Tooltip
          contentStyle={{
            background: tooltipBg,
            border: `1px solid ${tooltipBorder}`,
            borderRadius: 8,
            fontSize: 12,
          }}
          labelStyle={{ color: textColor }}
          formatter={(value: number, name: string) => {
            if (name === 'yhat') return [fmt(value), 'Forecast']
            if (name === 'lower') return [fmt(value), 'Lower 95%']
            if (name === 'ci_band') return [fmt(value + 0), 'CI Width']
            return [fmt(value), name]
          }}
        />
        {/* CI ribbon: transparent base + amber band stacked on top */}
        <Area
          dataKey="lower"
          stackId="ci"
          stroke="none"
          fill="transparent"
          legendType="none"
          isAnimationActive={false}
        />
        <Area
          dataKey="ci_band"
          stackId="ci"
          stroke="none"
          fill="#F59E0B"
          fillOpacity={0.18}
          legendType="none"
          isAnimationActive={false}
        />
        {/* Forecast line */}
        <Line
          dataKey="yhat"
          stroke="#F59E0B"
          strokeWidth={2.5}
          dot={false}
          name="yhat"
          isAnimationActive={false}
        />
      </ComposedChart>
    </ResponsiveContainer>
  )
}
