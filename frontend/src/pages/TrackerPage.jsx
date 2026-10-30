import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client.js'
import BudgetChart from '../components/BudgetChart.jsx'
import DailyChart from '../components/DailyChart.jsx'
import { IconTrash } from '../components/Icons.jsx'
import { Empty, ErrorBox, Spinner } from '../components/Feedback.jsx'
import ScoreBadge from '../components/ScoreBadge.jsx'
import Section from '../components/Section.jsx'
import TrendChart from '../components/TrendChart.jsx'
import { useAsync } from '../hooks/useAsync.js'

export default function TrackerPage() {
  const t = useAsync(() => api.tracker(7), [])
  const scans = useAsync(() => api.listScans(50), [])
  const [metric, setMetric] = useState('sugar')
  const removeLog = async (id) => {
    await api.deleteLog(id)
    t.run()
  }

  if (t.loading) return <Spinner />
  if (t.error) return <ErrorBox error={t.error} onRetry={t.run} />
  const d = t.data
  const messages = d.members.flatMap((m) => m.messages)
  const anyLogs = d.members.some((m) => m.items_logged > 0)

  return (
    <div className="space-y-6">
      {messages.length > 0 && (
        <div className="rounded-2xl border border-warn-line bg-warn-bg px-5 py-4 text-sm text-warn-ink">
          {messages.map((m, i) => (
            <p key={i} className="font-semibold">{m}</p>
          ))}
        </div>
      )}

      <Section title="Weekly budget used (last 7 days)" subtitle="Packaged foods you logged, as % of each member's daily limit x 7">
        {anyLogs ? (
          <>
            <BudgetChart members={d.members} />
            <table className="mt-3 w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase text-muted">
                  <th className="py-1">Member</th><th className="py-1 text-right">Sugar</th><th className="py-1 text-right">Sodium</th>
                </tr>
              </thead>
              <tbody>
                {d.members.map((m) => (
                  <tr key={m.member} className="border-t border-line">
                    <td className="py-1">{m.member}</td>
                    <td className="py-1 text-right tabular-nums">{m.sugar_g} / {m.sugar_budget_g} g ({m.sugar_pct}%)</td>
                    <td className="py-1 text-right tabular-nums">{m.sodium_mg} / {m.sodium_budget_mg} mg ({m.sodium_pct}%)</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        ) : (
          <Empty title="Nothing logged this week">Use "Log this" on a scan result to start tracking.</Empty>
        )}
      </Section>

      {anyLogs && (
        <Section title="Day by day" subtitle="What each member ate from logged packaged foods"
          right={
            <select className="input w-auto py-1.5" value={metric} onChange={(e) => setMetric(e.target.value)} aria-label="Nutrient">
              <option value="sugar">Sugar (g)</option>
              <option value="sodium">Sodium (mg)</option>
            </select>
          }>
          <DailyChart daily={d.daily} members={d.members.map((m) => m.member)} metric={metric} limits={d.limits} />
        </Section>
      )}

      {d.recent_logs.length > 0 && (
        <Section title="Logged this week" subtitle="Remove anything logged by mistake">
          <ul className="divide-y divide-line">
            {d.recent_logs.map((l) => (
              <li key={l.id} className="flex items-center gap-3 py-2.5 text-sm">
                <span className="w-16 shrink-0 text-xs text-muted">{new Date(l.logged_at).toLocaleDateString(undefined, { weekday: 'short', day: 'numeric' })}</span>
                <span className="min-w-0 flex-1">
                  <span className="font-medium">{l.product_name || `Scan ${l.scan_id}`}</span>
                  <span className="block text-xs text-muted">{l.member} · {l.grams} g · {l.sugar_g ?? '–'} g sugar · {l.sodium_mg ?? '–'} mg sodium</span>
                </span>
                <button className="rounded-lg p-2 text-muted hover:bg-surface hover:text-bad-ink" onClick={() => removeLog(l.id)} aria-label="Delete log">
                  <IconTrash width={15} height={15} />
                </button>
              </li>
            ))}
          </ul>
        </Section>
      )}

      <Section title="Health score of recent scans">
        {d.score_trend.length >= 2 ? <TrendChart points={d.score_trend} /> : <Empty title="Scan at least two products to see a trend" />}
      </Section>

      <Section title={anyLogs ? 'Worst offenders eaten this week' : 'Lowest-scoring scans'}>
        {d.worst_offenders.length === 0 && <Empty title="No data yet" />}
        <ul className="divide-y divide-line">
          {d.worst_offenders.map((w) => (
            <li key={`${w.scan_id}-${w.member}`} className="flex items-center gap-3 py-2 text-sm">
              <ScoreBadge score={w.score} color={w.score >= 70 ? 'green' : w.score >= 50 ? 'amber' : 'red'} size="sm" />
              <span className="flex-1">
                <span className="font-semibold">{w.product}</span>
                {w.member && <span className="block text-xs text-muted">{w.member}: {w.sugar_g ?? '-'} g sugar, {w.sodium_mg ?? '-'} mg sodium</span>}
              </span>
              <Link className="text-xs font-semibold text-brand" to={`/?scan=${w.scan_id}`}>Open</Link>
            </li>
          ))}
        </ul>
      </Section>

      <Section title="Scan history">
        {scans.loading && <Spinner />}
        {scans.data?.length === 0 && <Empty title="No scans yet" />}
        <ul className="divide-y divide-line">
          {scans.data?.map((s) => (
            <li key={s.id} className="flex items-center gap-3 py-2 text-sm">
              <span className="w-10 text-xs text-muted">#{s.id}</span>
              <span className="flex-1">
                <span className="font-semibold">{s.product_name || 'Unnamed'}</span>
                <span className="block text-xs text-muted">{s.brand} · {new Date(s.created_at).toLocaleString()} · {s.source}</span>
              </span>
              <span className="tabular-nums font-bold">{s.score}</span>
              <Link className="text-xs font-semibold text-brand" to={`/?scan=${s.id}`}>Open</Link>
            </li>
          ))}
        </ul>
      </Section>
    </div>
  )
}
