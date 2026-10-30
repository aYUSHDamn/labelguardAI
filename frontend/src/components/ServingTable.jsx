const LEVEL = {
  high: { label: 'High', cls: 'bg-bad-bg text-bad-ink' },
  medium: { label: 'Medium', cls: 'bg-warn-bg text-warn-ink' },
  low: { label: 'Low', cls: 'bg-good-bg text-good-ink' },
}

export default function ServingTable({ serving }) {
  if (!serving.rows.length) return <p className="text-sm text-muted">No nutrition table was readable.</p>
  const liquid = serving.basis === 'per 100ml'
  const unit = liquid ? '100 ml' : '100 g'
  return (
    <div>
      {serving.notes.length > 0 && (
        <ul className="mb-4 space-y-1.5 rounded-xl border border-warn-line bg-warn-bg px-4 py-3 text-sm text-warn-ink">
          {serving.notes.map((n, i) => (
            <li key={i}>{n}</li>
          ))}
        </ul>
      )}
      <div className="overflow-x-auto rounded-xl border border-line">
        <table className="w-full text-sm">
          <thead className="bg-surface text-left text-xs font-semibold uppercase tracking-wider text-muted">
            <tr>
              <th className="px-4 py-2.5">Nutrient</th>
              <th className="px-4 py-2.5 text-right">Per {unit}</th>
              <th className="px-4 py-2.5 text-right">
                Per serving{serving.serving_size_g ? ` (${serving.serving_size_g}${liquid ? ' ml' : ' g'})` : ''}
              </th>
              <th className="px-4 py-2.5 text-right">Level</th>
            </tr>
          </thead>
          <tbody>
            {serving.rows.map((r) => {
              const lv = LEVEL[r.level_per_100g]
              return (
                <tr key={r.nutrient} className="border-t border-line">
                  <td className={`px-4 py-2.5 ${r.hidden_by_small_serving ? 'font-semibold' : ''}`}>{r.label}</td>
                  <td className="px-4 py-2.5 text-right tabular-nums">{fmt(r.per_100g)} <span className="text-muted">{r.per_100g != null ? r.unit : ''}</span></td>
                  <td className="px-4 py-2.5 text-right tabular-nums">
                    {fmt(r.per_serving)} <span className="text-muted">{r.per_serving != null ? r.unit : ''}</span>
                    {r.per_serving_computed && <span className="text-muted" title="Calculated from per-100g and serving size">*</span>}
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    {lv && <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${lv.cls}`}>{lv.label}</span>}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-xs text-muted">* calculated from per-{unit} values × serving size. Levels use UK FSA traffic-light thresholds.</p>
    </div>
  )
}

const fmt = (v) => (v == null ? '–' : Number.isInteger(v) ? v : Number(v).toFixed(1))
