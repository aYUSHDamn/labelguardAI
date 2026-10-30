import { Link } from 'react-router-dom'
import { api } from '../api/client.js'
import { Empty, ErrorBox, Spinner } from '../components/Feedback.jsx'
import ScoreBadge from '../components/ScoreBadge.jsx'
import Section from '../components/Section.jsx'
import { useAsync } from '../hooks/useAsync.js'

const colorFor = (s) => (s >= 70 ? 'green' : s >= 50 ? 'amber' : 'red')

// Patterns across everything scanned. Pure aggregation over the rules output, no AI.
export default function InsightsPage() {
  const ins = useAsync(() => api.insights(), [])
  if (ins.loading) return <Spinner />
  if (ins.error) return <ErrorBox error={ins.error} onRetry={ins.run} />
  const d = ins.data
  if (!d.scan_count) return <Empty title="No scans yet">Scan a few labels and patterns will show up here.</Empty>

  const maxSugar = Math.max(1, ...d.top_sugar_names.map(([, n]) => n))
  const maxAdd = Math.max(1, ...d.top_additives.map(([, n]) => n))

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-3">
        <Stat label="Products scanned" value={d.scan_count} />
        <Stat label="Average health score" value={`${d.avg_score}/100`} />
        <Stat label="Misleading claims caught" value={d.misleading_claims} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Section title="Hidden sugar names you meet most" subtitle="Across all scanned labels">
          <Bars rows={d.top_sugar_names} max={maxSugar} color="var(--series-1)" empty="No sugar ingredients found yet." />
        </Section>
        <Section title="Flagged additives you meet most" subtitle="Medium or high concern">
          <Bars rows={d.top_additives} max={maxAdd} color="var(--series-2)" empty="No flagged additives yet." />
        </Section>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Section title="Average score by category" subtitle="Lowest first: where swaps help most">
          <div className="space-y-2.5">
            {d.category_scores.map(([cat, avg, n]) => (
              <div key={cat} className="flex items-center gap-3 text-sm">
                <span className="w-40 shrink-0 capitalize">{cat}</span>
                <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-surface">
                  <div className={`h-full rounded-full ${avg >= 70 ? 'bg-good' : avg >= 50 ? 'bg-warn' : 'bg-bad'}`} style={{ width: `${avg}%` }} />
                </div>
                <span className="w-16 text-right font-semibold tabular-nums">{avg}<span className="font-normal text-muted"> ({n})</span></span>
              </div>
            ))}
          </div>
        </Section>
        <Section title="Verdicts per family member" subtitle="Out of every product scanned">
          <div className="space-y-3">
            {d.member_status.map((m) => {
              const total = m.SAFE + m.WARN + m.AVOID || 1
              return (
                <div key={m.member}>
                  <div className="mb-1 flex justify-between text-sm"><span className="font-semibold">{m.member}</span>
                    <span className="text-xs text-muted">{m.SAFE} safe · {m.WARN} caution · {m.AVOID} avoid</span></div>
                  <div className="flex h-3 gap-0.5 overflow-hidden rounded-full">
                    {m.SAFE > 0 && <div className="bg-good" style={{ width: `${(m.SAFE / total) * 100}%` }} title={`${m.SAFE} safe`} />}
                    {m.WARN > 0 && <div className="bg-warn" style={{ width: `${(m.WARN / total) * 100}%` }} title={`${m.WARN} caution`} />}
                    {m.AVOID > 0 && <div className="bg-bad" style={{ width: `${(m.AVOID / total) * 100}%` }} title={`${m.AVOID} avoid`} />}
                  </div>
                </div>
              )
            })}
          </div>
        </Section>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Section title="Best scanned" className="lg:col-span-1"><ProductList items={d.best} /></Section>
        <Section title="Worst scanned" className="lg:col-span-1"><ProductList items={d.worst} /></Section>
        <Section title="Claims that misled most" className="lg:col-span-1">
          {d.top_misleading_claims.length ? (
            <ul className="space-y-2 text-sm">
              {d.top_misleading_claims.map(([c, n]) => <li key={c} className="flex justify-between gap-2"><span>“{c}”</span><span className="text-muted">{n}×</span></li>)}
            </ul>
          ) : <p className="text-sm text-muted">None yet.</p>}
        </Section>
      </div>
    </div>
  )
}

function Stat({ label, value }) {
  return (
    <div className="card p-5">
      <p className="text-xs font-semibold uppercase tracking-wider text-muted">{label}</p>
      <p className="mt-1 text-3xl font-extrabold tracking-tight">{value}</p>
    </div>
  )
}

function Bars({ rows, max, color, empty }) {
  if (!rows.length) return <p className="text-sm text-muted">{empty}</p>
  return (
    <div className="space-y-2.5">
      {rows.map(([name, n]) => (
        <div key={name} className="flex items-center gap-3 text-sm">
          <span className="w-44 shrink-0 truncate capitalize" title={name}>{name}</span>
          <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-surface">
            <div className="h-full rounded-full" style={{ width: `${(n / max) * 100}%`, background: color }} />
          </div>
          <span className="w-8 text-right tabular-nums text-muted">{n}</span>
        </div>
      ))}
    </div>
  )
}

function ProductList({ items }) {
  return (
    <ul className="space-y-2.5">
      {items.map((p) => (
        <li key={p.scan_id} className="flex items-center gap-3">
          <ScoreBadge score={p.score} color={colorFor(p.score)} size="sm" />
          <Link to={`/?scan=${p.scan_id}`} className="min-w-0 truncate text-sm font-medium hover:text-brand">{p.product}</Link>
        </li>
      ))}
    </ul>
  )
}
