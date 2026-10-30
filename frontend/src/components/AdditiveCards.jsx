const CONCERN = {
  high: { tag: 'bg-bad-bg text-bad-ink', label: 'High concern' },
  medium: { tag: 'bg-warn-bg text-warn-ink', label: 'Medium concern' },
  low: { tag: 'bg-good-bg text-good-ink', label: 'Low concern' },
  unknown: { tag: 'bg-surface text-muted', label: 'Not in our table' },
}

export default function AdditiveCards({ additives }) {
  if (!additives.length) return <p className="text-sm text-muted">No INS / E-number additives found.</p>
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {additives.map((a) => {
        const c = CONCERN[a.concern] || CONCERN.unknown
        return (
          <div key={a.code} className="rounded-xl border border-line p-3.5">
            <div className="flex items-start justify-between gap-2">
              <span className="font-semibold leading-snug">{a.name}</span>
              <span className="shrink-0 rounded-md bg-surface px-1.5 py-0.5 text-[11px] font-semibold text-muted">INS {a.code}</span>
            </div>
            <p className="mt-1 text-sm text-muted">{a.purpose}</p>
            <span className={`mt-2 inline-block rounded-full px-2 py-0.5 text-[11px] font-semibold ${c.tag}`}>{c.label}</span>
            {a.note && <p className="mt-1.5 text-xs text-muted">{a.note}</p>}
          </div>
        )
      })}
    </div>
  )
}
