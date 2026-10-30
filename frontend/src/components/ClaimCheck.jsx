import { IconAlert, IconCheck, IconInfo } from './Icons.jsx'

const V = {
  ok: { icon: IconCheck, tag: 'bg-good-bg text-good-ink', iconCls: 'text-good', label: 'Holds up' },
  misleading: { icon: IconAlert, tag: 'bg-bad-bg text-bad-ink', iconCls: 'text-bad', label: 'Misleading' },
  marketing: { icon: IconInfo, tag: 'bg-surface text-muted', iconCls: 'text-muted', label: 'Just marketing' },
  unknown: { icon: IconInfo, tag: 'bg-surface text-muted', iconCls: 'text-muted', label: "Can't check" },
}

export default function ClaimCheck({ claims }) {
  if (!claims.length) return <p className="text-sm text-muted">No front-of-pack claims were found.</p>
  return (
    <ul className="space-y-3">
      {claims.map((c, i) => {
        const v = V[c.verdict] || V.unknown
        const Icon = v.icon
        return (
          <li key={i} className="flex items-start gap-3 rounded-xl border border-line p-3.5 text-sm">
            <Icon className={`mt-0.5 shrink-0 ${v.iconCls}`} />
            <span className="flex-1">
              <span className="flex flex-wrap items-center gap-2">
                <span className="font-semibold">“{c.claim}”</span>
                <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${v.tag}`}>{v.label}</span>
              </span>
              <span className="mt-0.5 block text-muted">{c.reason}</span>
            </span>
          </li>
        )
      })}
    </ul>
  )
}
