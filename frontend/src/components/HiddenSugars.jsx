export default function HiddenSugars({ sugars }) {
  if (!sugars.length) return <p className="text-sm text-muted">No sugar ingredients found in the list.</p>
  return (
    <div>
      {sugars.length >= 2 && (
        <p className="mb-4 rounded-xl border border-warn-line bg-warn-bg px-4 py-3 text-sm text-warn-ink">
          Sugar appears under <b>{sugars.length} different names</b>. Splitting sugar lets each one sit lower in the ingredient list.
        </p>
      )}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {sugars.map((s) => (
          <div key={s.alias} className="rounded-xl border border-line p-3.5">
            <div className="flex items-center justify-between gap-2">
              <span className="font-semibold capitalize">{s.alias}</span>
              <span className="text-xs text-muted">#{s.position} on list</span>
            </div>
            <p className="mt-1 text-sm text-muted">{s.note}</p>
            {s.hidden && <span className="mt-2 inline-block rounded-full bg-warn-bg px-2 py-0.5 text-[11px] font-semibold text-warn-ink">Hidden name</span>}
          </div>
        ))}
      </div>
    </div>
  )
}
