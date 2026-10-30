import { useState } from 'react'
import StatusPill, { STATUS } from './StatusPill.jsx'

// One row per household member: Safe / Caution / Avoid with every reason and its evidence.
export default function MemberVerdicts({ members, selected }) {
  const shown = selected && selected !== 'all' ? members.filter((m) => m.member === selected) : members
  return (
    <div className="divide-y divide-line overflow-hidden rounded-xl border border-line">
      {shown.map((m) => (
        <MemberRow key={m.member} m={m} defaultOpen={shown.length === 1} />
      ))}
    </div>
  )
}

function MemberRow({ m, defaultOpen }) {
  const [open, setOpen] = useState(defaultOpen)
  const s = STATUS[m.status]
  const initials = m.member.slice(0, 2).toUpperCase()
  return (
    <div className="relative">
      <span className={`absolute inset-y-0 left-0 w-1 ${s.bar}`} aria-hidden />
      <button className="flex w-full items-center gap-3 py-3.5 pl-5 pr-4 text-left transition hover:bg-surface/70"
        onClick={() => setOpen(!open)} aria-expanded={open}>
        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-surface text-xs font-bold text-muted">{initials}</span>
        <span className="min-w-0 flex-1">
          <span className="flex items-center gap-2">
            <span className="font-semibold">{m.member}</span>
            <span className="text-xs capitalize text-muted">{m.relation}</span>
          </span>
          <span className="block truncate text-sm text-muted">{m.summary}</span>
        </span>
        <StatusPill status={m.status} />
        {m.flags.length > 0 && (
          <span className={`text-muted transition ${open ? 'rotate-180' : ''}`} aria-hidden>▾</span>
        )}
      </button>
      {open && m.flags.length > 0 && (
        <ul className="space-y-2.5 bg-surface/50 py-3 pl-[68px] pr-4">
          {m.flags.map((f, i) => (
            <li key={i} className="flex items-start gap-2.5 text-sm">
              <StatusPill status={f.status} small />
              <span className="min-w-0">
                {f.reason}
                <span className="block text-xs text-muted">Found: {f.evidence}</span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
