import {
  Area,
  CartesianGrid,
  ComposedChart,
  LabelList,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useAppStore } from '../../store/useAppStore'
import type { ForecastPoint, ObservationPoint } from '../../types'

interface Props {
  data: ForecastPoint[]
  historical?: ObservationPoint[]
}

const fmt = (n: number) => n.toLocaleString(undefined, { maximumFractionDigits: 0 })

export default function ForecastChart({ data, historical }: Props) {
  const theme = useAppStore((s) => s.theme)
  const chartSettings = useAppStore((s) => s.chartSettings)
  const { historicalColor, forecastColor, showDataLabels, yAxisScale } = chartSettings

  const gridColor = theme === 'dark' ? '#334155' : '#E2E8F0'
  const textColor = theme === 'dark' ? '#94A3B8' : '#64748B'
  const tooltipBg = theme === 'dark' ? '#1E293B' : '#FFFFFF'
  const tooltipBorder = theme === 'dark' ? '#334155' : '#E2E8F0'

  // Build merged chart array
  const merged: Record<string, unknown>[] = []

  if (historical && historical.length > 0) {
    historical.forEach((d) => {
      merged.push({
        date: d.date,
        historical: d.volume,
      })
    })
  }

  data.forEach((d) => {
    merged.push({
      date: d.date,
      yhat: d.yhat,
      lower: d.yhat_lower,
      ci_band: Math.max(0, d.yhat_upper - d.yhat_lower),
    })
  })

  const lastHistDate = historical && historical.length > 0
    ? historical[historical.length - 1].date
    : null

  // Determine tick interval based on total data points
  const totalPoints = merged.length
  const tickInterval = totalPoints > 600 ? 59 : totalPoints > 300 ? 29 : 13

  return (
    <ResponsiveContainer width="100%" height={420}>
      <ComposedChart data={merged} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 11, fill: textColor }}
          tickFormatter={(v: string) => v.slice(0, 7)}
          interval={tickInterval}
        />
        <YAxis
          tick={{ fontSize: 11, fill: textColor }}
          tickFormatter={fmt}
          width={72}
          scale={yAxisScale === 'log' ? 'log' : 'auto'}
          domain={yAxisScale === 'log' ? ['auto', 'auto'] : undefined}
          allowDataOverflow={yAxisScale === 'log'}
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
            if (name === 'historical') return [fmt(value), 'Historical']
            if (name === 'yhat') return [fmt(value), 'Forecast']
            if (name === 'lower') return [fmt(value), 'Lower 95%']
            if (name === 'ci_band') return [fmt(value), 'CI Width']
            return [fmt(value), name]
          }}
        />

        {/* CI ribbon */}
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
          fill={forecastColor}
          fillOpacity={0.18}
          legendType="none"
          isAnimationActive={false}
        />

        {/* Historical line */}
        {historical && historical.length > 0 && (
          <Line
            dataKey="historical"
            stroke={historicalColor}
            strokeWidth={1.8}
            dot={false}
            name="historical"
            isAnimationActive={false}
            connectNulls={false}
          >
            {showDataLabels && <LabelList dataKey="historical" position="top" style={{ fontSize: 9, fill: textColor }} />}
          </Line>
        )}

        {/* Forecast line */}
        <Line
          dataKey="yhat"
          stroke={forecastColor}
          strokeWidth={2.5}
          dot={false}
          name="yhat"
          isAnimationActive={false}
          connectNulls={false}
        >
          {showDataLabels && <LabelList dataKey="yhat" position="top" style={{ fontSize: 9, fill: textColor }} />}
        </Line>

        {/* Divider between historical and forecast */}
        {lastHistDate && (
          <ReferenceLine
            x={lastHistDate}
            stroke="#64748B"
            strokeDasharray="4 2"
            label="Today"
          />
        )}
      </ComposedChart>
    </ResponsiveContainer>
  )
}
