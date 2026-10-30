import { IconAlert, IconCheck, IconStop } from './Icons.jsx'

// Status is never colour-only: every pill has an icon and a text label.
export const STATUS = {
  SAFE: { pill: 'bg-good-bg text-good-ink border-good-line', icon: IconCheck, label: 'Safe', bar: 'bg-good' },
  WARN: { pill: 'bg-warn-bg text-warn-ink border-warn-line', icon: IconAlert, label: 'Caution', bar: 'bg-warn' },
  AVOID: { pill: 'bg-bad-bg text-bad-ink border-bad-line', icon: IconStop, label: 'Avoid', bar: 'bg-bad' },
}

export default function StatusPill({ status, small = false }) {
  const s = STATUS[status] || STATUS.WARN
  const Icon = s.icon
  return (
    <span className={`inline-flex shrink-0 items-center gap-1 rounded-full border font-semibold ${s.pill} ${small ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs'}`}>
      <Icon width={small ? 11 : 13} height={small ? 11 : 13} strokeWidth={2.5} />
      {s.label}
    </span>
  )
}
