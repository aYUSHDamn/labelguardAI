import { IconAlert, IconCheck, IconInfo } from './Icons.jsx'

const V = {
  ok: { icon: IconCheck, tag: 'bg-good-bg text-good-ink', iconCls: 'text-good', label: 'Backed up' },
  misleading: { icon: IconAlert, tag: 'bg-bad-bg text-bad-ink', iconCls: 'text-bad', label: 'Misleading' },
  marketing: { icon: IconInfo, tag: 'bg-surface text-muted', iconCls: 'text-muted', label: 'Just marketing' },
  unknown: { icon: IconInfo, tag: 'bg-surface text-muted', iconCls: 'text-muted', label: "Can't check" },
}

// What the FRONT of the pack shows/promises vs what the BACK actually says.
export default function FrontBackCheck({ items }) {
  if (!items.length) {
    return (
      <p className="text-sm text-muted">
        Add a photo of the <b className="text-ink">front</b> of the pack along with the back (up to 3 photos) and we'll check
        every picture and promise on the front against the ingredient list.
      </p>
    )
  }
  const bad = items.filter((i) => i.verdict === 'misleading').length
  const pictures = items.filter((i) => i.kind === 'picture')
  const messages = items.filter((i) => i.kind === 'message')
  return (
    <div>
      <p className={`mb-4 rounded-xl border px-4 py-3 text-sm ${bad ? 'border-bad-line bg-bad-bg text-bad-ink' : 'border-good-line bg-good-bg text-good-ink'}`}>
        {bad ? <><b>{bad} of {items.length}</b> front-of-pack promises don't match the back of the pack.</> : 'The front of the pack matches the back.'}
      </p>
      <div className="grid gap-6 md:grid-cols-2">
        <Column title="Pictured or named on the front" items={pictures} />
        <Column title="What the front suggests" items={messages} />
      </div>
    </div>
  )
}

function Column({ title, items }) {
  if (!items.length) return null
  return (
    <div>
      <p className="label">{title}</p>
      <ul className="space-y-2.5">
        {items.map((it, i) => {
          const v = V[it.verdict] || V.unknown
          const Icon = v.icon
          return (
            <li key={i} className="flex items-start gap-3 rounded-xl border border-line p-3.5 text-sm">
              <Icon className={`mt-0.5 shrink-0 ${v.iconCls}`} />
              <span className="min-w-0 flex-1">
                <span className="flex flex-wrap items-center gap-2">
                  <span className="font-semibold capitalize">{it.front}</span>
                  <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${v.tag}`}>{v.label}</span>
                </span>
                <span className="mt-0.5 block text-muted">{it.reason}</span>
                {it.evidence && <span className="mt-0.5 block text-xs text-muted">Back of pack: {it.evidence}</span>}
              </span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
