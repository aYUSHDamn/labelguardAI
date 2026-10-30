import { Bar, BarChart, CartesianGrid, LabelList, Legend, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

// Weekly budget used (%) per member. Both bars share ONE axis (percent of budget),
// so sugar and sodium are comparable without a dual axis. 100% line = the budget.
export default function BudgetChart({ members }) {
  const data = members.map((m) => ({ name: m.member, Sugar: m.sugar_pct, Sodium: m.sodium_pct, raw: m }))
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 16, right: 8, left: -12, bottom: 0 }} barGap={2} barCategoryGap="28%">
          <CartesianGrid vertical={false} stroke="var(--grid)" />
          <XAxis dataKey="name" tick={{ fill: 'var(--chart-text)', fontSize: 12 }} axisLine={false} tickLine={false} />
          <YAxis domain={[0, (dataMax) => Math.max(120, Math.ceil(dataMax / 20) * 20 + 20)]} tickFormatter={(v) => `${v}%`} tick={{ fill: 'var(--chart-text)', fontSize: 11 }} axisLine={false} tickLine={false} />
          <ReferenceLine y={100} stroke="var(--chart-text)" strokeDasharray="4 4"
            label={{ value: 'weekly budget', position: 'insideTopRight', fill: 'var(--chart-text)', fontSize: 11 }} />
          <Tooltip cursor={{ fill: 'var(--grid)', opacity: 0.4 }} content={<BudgetTooltip />} />
          <Legend wrapperStyle={{ fontSize: 12, color: 'var(--chart-text)' }} iconType="circle" />
          <Bar dataKey="Sugar" fill="var(--series-1)" radius={[4, 4, 0, 0]} maxBarSize={36} isAnimationActive={false}>
            <LabelList dataKey="Sugar" position="top" formatter={(v) => `${v}%`} style={{ fill: 'var(--chart-text)', fontSize: 11 }} />
          </Bar>
          <Bar dataKey="Sodium" fill="var(--series-2)" radius={[4, 4, 0, 0]} maxBarSize={36} isAnimationActive={false}>
            <LabelList dataKey="Sodium" position="top" formatter={(v) => `${v}%`} style={{ fill: 'var(--chart-text)', fontSize: 11 }} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

function BudgetTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const m = payload[0].payload.raw
  return (
    <div className="rounded-xl border border-line bg-card p-2 text-xs shadow">
      <p className="font-bold">{m.member}</p>
      <p>Sugar: {m.sugar_g} g of {m.sugar_budget_g} g ({m.sugar_pct}%)</p>
      <p>Sodium: {m.sodium_mg} mg of {m.sodium_budget_mg} mg ({m.sodium_pct}%)</p>
      <p className="text-muted">{m.items_logged} item(s) logged</p>
    </div>
  )
}
