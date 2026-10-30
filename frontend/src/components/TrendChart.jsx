import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

// Score of the last N scans (single series, so no legend: the section title names it).
// Dashed lines mark the grade thresholds (50 = amber, 70 = green).
export default function TrendChart({ points }) {
  const data = points.map((p, i) => ({ ...p, idx: i + 1 }))
  return (
    <div className="h-56 w-full">
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 12, right: 12, left: -16, bottom: 0 }}>
          <CartesianGrid vertical={false} stroke="var(--grid)" />
          <XAxis dataKey="idx" tick={{ fill: 'var(--chart-text)', fontSize: 11 }} axisLine={false} tickLine={false}
            label={{ value: 'scan #', position: 'insideBottomRight', offset: -2, fill: 'var(--chart-text)', fontSize: 11 }} />
          <YAxis domain={[0, 100]} ticks={[0, 25, 50, 70, 100]} tick={{ fill: 'var(--chart-text)', fontSize: 11 }} axisLine={false} tickLine={false} />
          <ReferenceLine y={70} stroke="var(--chart-text)" strokeDasharray="4 4"
            label={{ value: 'good', position: 'insideTopRight', fill: 'var(--chart-text)', fontSize: 10 }} />
          <ReferenceLine y={50} stroke="var(--chart-text)" strokeDasharray="4 4"
            label={{ value: 'okay', position: 'insideTopRight', fill: 'var(--chart-text)', fontSize: 10 }} />
          <Tooltip cursor={{ stroke: 'var(--chart-text)', strokeDasharray: '3 3' }} content={<TrendTooltip />} />
          <Line type="linear" isAnimationActive={false} dataKey="score" stroke="var(--series-1)" strokeWidth={2}
            dot={{ r: 4, fill: 'var(--series-1)', stroke: 'rgb(var(--card))', strokeWidth: 2 }} activeDot={{ r: 6 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

function TrendTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const p = payload[0].payload
  return (
    <div className="rounded-xl border border-line bg-card p-2 text-xs shadow">
      <p className="font-bold">{p.product}</p>
      <p>Score {p.score}/100</p>
      <p className="text-muted">{new Date(p.created_at).toLocaleString()}</p>
    </div>
  )
}
