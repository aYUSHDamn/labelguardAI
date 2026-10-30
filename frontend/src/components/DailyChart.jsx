import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

const SERIES = ['var(--series-1)', 'var(--series-2)', 'var(--series-3)', 'var(--series-4)']

// Day-by-day intake per member for one nutrient. Members keep a fixed colour (slot order),
// so the colours don't change when you switch nutrient.
export default function DailyChart({ daily, members, metric, limits }) {
  const unit = metric === 'sugar' ? 'g' : 'mg'
  const data = daily.map((d) => {
    const row = { label: d.label }
    members.forEach((m) => { row[m] = d[`${m}|${metric}`] })
    return row
  })
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 10, right: 8, left: -8, bottom: 0 }} barGap={2} barCategoryGap="22%">
          <CartesianGrid vertical={false} stroke="var(--grid)" />
          <XAxis dataKey="label" tick={{ fill: 'var(--chart-text)', fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fill: 'var(--chart-text)', fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={(v) => `${v}${unit}`} />
          <Tooltip cursor={{ fill: 'var(--grid)', opacity: 0.4 }} content={<DailyTooltip unit={unit} metric={metric} limits={limits} />} />
          <Legend wrapperStyle={{ fontSize: 12, color: 'var(--chart-text)' }} iconType="circle" />
          {members.slice(0, 4).map((m, i) => (
            <Bar key={m} dataKey={m} fill={SERIES[i]} radius={[4, 4, 0, 0]} maxBarSize={22} isAnimationActive={false} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

function DailyTooltip({ active, payload, label, unit, metric, limits }) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-xl border border-line bg-card p-2.5 text-xs shadow">
      <p className="mb-1 font-bold">{label}</p>
      {payload.map((p) => {
        const lim = limits?.[p.dataKey]?.[metric === 'sugar' ? 'sugar_g' : 'sodium_mg']
        return (
          <p key={p.dataKey} className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full" style={{ background: p.color }} />
            {p.dataKey}: <b>{p.value} {unit}</b>{lim ? <span className="text-muted"> of {lim} {unit} daily limit</span> : null}
          </p>
        )
      })}
    </div>
  )
}
