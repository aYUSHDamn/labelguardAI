// Score ring (red / amber / green) with the grade label beside it, never colour alone.
const COLORS = { green: 'rgb(var(--good))', amber: 'rgb(var(--warn))', red: 'rgb(var(--bad))' }
const PILL = {
  green: 'bg-good-bg text-good-ink border-good-line',
  amber: 'bg-warn-bg text-warn-ink border-warn-line',
  red: 'bg-bad-bg text-bad-ink border-bad-line',
}

export default function ScoreBadge({ score, color, label, size = 'lg' }) {
  const dim = size === 'lg' ? 128 : 52
  const stroke = size === 'lg' ? 11 : 5
  const r = (dim - stroke) / 2
  const c = 2 * Math.PI * r
  const pct = Math.max(0, Math.min(100, score)) / 100
  return (
    <div className={`flex shrink-0 ${size === 'lg' ? 'flex-col items-center gap-2' : 'items-center'}`}>
      <div className="relative" style={{ width: dim, height: dim }} aria-label={`Score ${score} out of 100${label ? `, ${label}` : ''}`}>
        <svg width={dim} height={dim} className="-rotate-90">
          <circle cx={dim / 2} cy={dim / 2} r={r} stroke="rgb(var(--line))" strokeWidth={stroke} fill="none" />
          <circle cx={dim / 2} cy={dim / 2} r={r} stroke={COLORS[color] || COLORS.amber} strokeWidth={stroke}
            fill="none" strokeLinecap="round" strokeDasharray={`${c * pct} ${c}`} />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`font-extrabold leading-none tracking-tight ${size === 'lg' ? 'text-4xl' : 'text-[15px]'}`}>{score}</span>
          {size === 'lg' && <span className="mt-0.5 text-xs text-muted">out of 100</span>}
        </div>
      </div>
      {size === 'lg' && label && (
        <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${PILL[color] || PILL.amber}`}>{label}</span>
      )}
    </div>
  )
}
