import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useAppStore } from '../../store/useAppStore'

const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

interface Props {
  monthlyFactors: Record<string, number>
  weeklyPattern: Array<{ day: string; effect: number }>
}

export default function SeasonalityChart({ monthlyFactors, weeklyPattern }: Props) {
  const theme = useAppStore((s) => s.theme)
  const gridColor = theme === 'dark' ? '#334155' : '#E2E8F0'
  const textColor = theme === 'dark' ? '#94A3B8' : '#64748B'
  const tooltipBg = theme === 'dark' ? '#1E293B' : '#FFFFFF'
  const tooltipBorder = theme === 'dark' ? '#334155' : '#E2E8F0'

  const monthData = Object.entries(monthlyFactors)
    .sort(([a], [b]) => Number(a) - Number(b))
    .map(([m, factor]) => ({
      month: MONTH_NAMES[Number(m) - 1] ?? m,
      factor: Math.round((factor - 1) * 100),
    }))

  const weekData = weeklyPattern.map((d) => ({
    day: d.day.slice(0, 3),
    effect: Math.round(d.effect),
  }))

  const tooltipStyle = {
    background: tooltipBg,
    border: `1px solid ${tooltipBorder}`,
    borderRadius: 8,
    fontSize: 12,
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Monthly seasonality */}
      <div>
        <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">
          Monthly Pattern (% vs. average)
        </h4>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={monthData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
            <XAxis dataKey="month" tick={{ fontSize: 11, fill: textColor }} />
            <YAxis
              tick={{ fontSize: 11, fill: textColor }}
              tickFormatter={(v: number) => `${v > 0 ? '+' : ''}${v}%`}
              width={52}
            />
            <Tooltip
              contentStyle={tooltipStyle}
              formatter={(v: number) => [`${v > 0 ? '+' : ''}${v}%`, 'vs. avg']}
            />
            <ReferenceLine y={0} stroke={gridColor} />
            <Bar dataKey="factor" radius={[3, 3, 0, 0]} maxBarSize={28}>
              {monthData.map((entry, i) => (
                <Cell key={i} fill={entry.factor >= 0 ? '#2563EB' : '#EF4444'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Weekly seasonality */}
      <div>
        <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">
          Weekly Pattern (% vs. average)
        </h4>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={weekData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
            <XAxis dataKey="day" tick={{ fontSize: 11, fill: textColor }} />
            <YAxis
              tick={{ fontSize: 11, fill: textColor }}
              tickFormatter={(v: number) => `${v > 0 ? '+' : ''}${v}%`}
              width={52}
            />
            <Tooltip
              contentStyle={tooltipStyle}
              formatter={(v: number) => [`${v > 0 ? '+' : ''}${v}%`, 'vs. avg']}
            />
            <ReferenceLine y={0} stroke={gridColor} />
            <Bar dataKey="effect" radius={[3, 3, 0, 0]} maxBarSize={28}>
              {weekData.map((entry, i) => (
                <Cell key={i} fill={entry.effect >= 0 ? '#059669' : '#F59E0B'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
