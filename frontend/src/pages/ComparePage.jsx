import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client.js'
import { Empty, ErrorBox, Spinner } from '../components/Feedback.jsx'
import { IconClose } from '../components/Icons.jsx'
import ScoreBadge from '../components/ScoreBadge.jsx'
import Section from '../components/Section.jsx'
import StatusPill from '../components/StatusPill.jsx'
import { useApp } from '../context/AppContext.jsx'
import { useAsync } from '../hooks/useAsync.js'

const NUTRIENTS = [
  ['sugar_g', 'Sugar', 'g', 'lower'],
  ['sodium_mg', 'Sodium', 'mg', 'lower'],
  ['sat_fat_g', 'Saturated fat', 'g', 'lower'],
  ['energy_kcal', 'Energy', 'kcal', 'lower'],
  ['protein_g', 'Protein', 'g', 'higher'],
  ['fiber_g', 'Fibre', 'g', 'higher'],
]
const SERIES = ['var(--series-1)', 'var(--series-2)', 'var(--series-3)', 'var(--series-4)']

export default function ComparePage() {
  const { member } = useApp()
  const scans = useAsync(() => api.listScans(100), [])
  const [ids, setIds] = useState([null, null])
  const [state, setState] = useState({ loading: false, data: null, error: null })

  const chosen = ids.filter(Boolean)
  const setAt = (i, v) => setIds((prev) => prev.map((x, j) => (j === i ? v : x)))
  const run = async () => {
    setState({ loading: true, data: null, error: null })
    try {
      setState({ loading: false, data: await api.compare(chosen, member), error: null })
    } catch (error) {
      setState({ loading: false, data: null, error })
    }
  }
  const d = state.data

  return (
    <div className="space-y-6">
      <Section title="Compare products" subtitle="Pick 2-4 scanned products. Winner = safest verdict for the selected member, then the higher score. No AI.">
        {scans.loading && <Spinner />}
        <ErrorBox error={scans.error} onRetry={scans.run} />
        {scans.data && scans.data.length < 2 && <Empty title="Scan at least two products first"><Link to="/" className="text-brand hover:underline">Go to Scan</Link></Empty>}
        {scans.data?.length >= 2 && (
          <>
            <div className="grid gap-3 sm:grid-cols-2">
              {ids.map((v, i) => (
                <div key={i} className="flex items-end gap-2">
                  <label className="block flex-1">
                    <span className="label">Product {i + 1}</span>
                    <select className="input" value={v ?? ''} onChange={(e) => setAt(i, e.target.value ? Number(e.target.value) : null)}>
                      <option value="">Choose a scan...</option>
                      {scans.data.map((s) => (
                        <option key={s.id} value={s.id} disabled={ids.includes(s.id) && v !== s.id}>
                          #{s.id} {s.product_name || 'Unnamed'} ({s.score}/100)
                        </option>
                      ))}
                    </select>
                  </label>
                  {ids.length > 2 && (
                    <button className="mb-1 rounded-lg p-2 text-muted hover:bg-surface" onClick={() => setIds(ids.filter((_, j) => j !== i))} aria-label="Remove">
                      <IconClose width={16} height={16} />
                    </button>
                  )}
                </div>
              ))}
            </div>
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <button className="btn-primary" disabled={chosen.length < 2 || state.loading} onClick={run}>
                {state.loading ? 'Comparing...' : `Compare ${chosen.length || ''} products`}
              </button>
              {ids.length < 4 && <button className="btn-ghost" onClick={() => setIds([...ids, null])}>+ Add another</button>}
              <span className="text-xs text-muted">For: {member === 'all' ? 'whole family (worst verdict)' : member} · change in the sidebar</span>
            </div>
          </>
        )}
      </Section>

      <ErrorBox error={state.error} />
      {d && (
        <>
          <div className="flex items-start gap-3 rounded-2xl border border-good-line bg-good-bg px-5 py-4">
            <span className="text-2xl" aria-hidden>🏆</span>
            <p className="text-sm"><b className="text-good-ink">{d.winner_scan_id ? 'Best pick: ' : ''}</b>{d.reason}</p>
          </div>

          <div className={`grid gap-4 ${d.items.length === 2 ? 'md:grid-cols-2' : d.items.length === 3 ? 'md:grid-cols-3' : 'md:grid-cols-2 xl:grid-cols-4'}`}>
            {d.items.map((s, i) => (
              <div key={s.scan_id} className={`card ${d.winner_scan_id === s.scan_id ? 'ring-2 ring-good' : ''}`}>
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-1.5 text-xs font-semibold text-muted">
                    <span className="h-2.5 w-2.5 rounded-full" style={{ background: SERIES[i] }} /> #{s.rank} of {d.items.length}
                  </span>
                  <StatusPill status={s.status} small />
                </div>
                <div className="mt-3 flex items-center gap-3">
                  <ScoreBadge score={s.score} color={s.color} size="sm" />
                  <div className="min-w-0">
                    <p className="font-semibold leading-snug">{s.product_name}</p>
                    <p className="text-xs text-muted">{s.brand} · {s.label}</p>
                  </div>
                </div>
                <dl className="mt-3 space-y-1 text-xs">
                  <Row k="Sugar sources" v={s.hidden_sugars.join(', ') || 'none'} />
                  <Row k="Flagged additives" v={s.additives_flagged.join(', ') || 'none'} />
                  <Row k="Misleading claims" v={s.misleading_claims.map((c) => `“${c}”`).join(', ') || 'none'} />
                </dl>
                {s.flags.length > 0 && (
                  <ul className="mt-3 space-y-1.5 border-t border-line pt-3">
                    {s.flags.slice(0, 4).map((f, j) => (
                      <li key={j} className="flex items-start gap-2 text-xs">
                        <StatusPill status={f.status} small />
                        <span>{f.member ? `${f.member}: ` : ''}{f.reason}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>

          <Section title="Nutrients side by side" subtitle="Per 100 g/ml. Each row has its own scale; the best value in a row is marked ✓.">
            <div className="space-y-5">
              {NUTRIENTS.map(([k, label, unit, better]) => {
                const vals = d.items.map((s) => s.nutrition_per_100g[k])
                const known = vals.filter((v) => v != null)
                if (!known.length) return null
                const max = Math.max(...known, 0.0001)
                const best = better === 'lower' ? Math.min(...known) : Math.max(...known)
                return (
                  <div key={k}>
                    <p className="mb-1.5 text-sm font-semibold">{label} <span className="font-normal text-muted">({better} is better)</span></p>
                    <div className="space-y-1.5">
                      {d.items.map((s, i) => {
                        const v = s.nutrition_per_100g[k]
                        return (
                          <div key={s.scan_id} className="flex items-center gap-3 text-xs">
                            <span className="w-32 shrink-0 truncate text-muted" title={s.product_name}>{s.product_name}</span>
                            <div className="h-3 flex-1 overflow-hidden rounded-r-full bg-surface">
                              {v != null && <div className="h-full rounded-r-full" style={{ width: `${Math.max(2, (v / max) * 100)}%`, background: SERIES[i] }} />}
                            </div>
                            <span className="w-20 text-right tabular-nums">
                              {v == null ? '–' : `${v} ${unit}`} {v != null && v === best && known.length > 1 ? <b className="text-good-ink">✓</b> : ''}
                            </span>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )
              })}
            </div>
          </Section>
        </>
      )}
    </div>
  )
}

function Row({ k, v }) {
  return (
    <div className="flex gap-2">
      <dt className="w-28 shrink-0 text-muted">{k}</dt>
      <dd className="min-w-0">{v}</dd>
    </div>
  )
}
