import { Link } from 'react-router-dom'
import { api } from '../api/client.js'
import { Empty, ErrorBox, Spinner } from '../components/Feedback.jsx'
import { IconAlert, IconPrint, IconShield } from '../components/Icons.jsx'
import { useAsync } from '../hooks/useAsync.js'

// One printable card per family member: show it to a shopkeeper, caterer or school.
export default function AllergyCardsPage() {
  const cards = useAsync(() => api.allergyCards(), [])
  if (cards.loading) return <Spinner />
  if (cards.error) return <ErrorBox error={cards.error} onRetry={cards.run} />
  const list = cards.data.cards

  return (
    <div className="space-y-6">
      <div className="no-print flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold tracking-tight">Allergy & diet cards</h1>
          <p className="text-sm text-muted">Print or screenshot a card to show at a shop, restaurant or school. Built from your <Link to="/profile" className="text-brand hover:underline">family profile</Link>.</p>
        </div>
        <button className="btn-primary" onClick={() => window.print()}><IconPrint width={16} height={16} /> Print cards</button>
      </div>
      {list.length === 0 && <Empty title="No family members yet" />}
      <div className="grid gap-6 md:grid-cols-2">
        {list.map((c) => (
          <article key={c.member} className="card overflow-hidden p-0">
            <header className="flex items-center gap-3 bg-brand px-5 py-4 text-brand-ink">
              <IconShield width={22} height={22} />
              <div>
                <p className="text-lg font-bold leading-tight">{c.member}</p>
                <p className="text-xs capitalize opacity-90">{c.relation}{c.age ? `, ${c.age} years` : ''}</p>
              </div>
            </header>
            <div className="space-y-4 p-5">
              {c.allergies.length > 0 ? (
                <div className="rounded-xl border border-bad-line bg-bad-bg p-3.5">
                  <p className="flex items-center gap-1.5 text-sm font-bold text-bad-ink"><IconAlert width={16} height={16} /> ALLERGIC TO</p>
                  {c.allergies.map((a) => (
                    <div key={a.name} className="mt-2">
                      <p className="font-semibold">{a.name}</p>
                      <p className="text-xs text-ink/75">Also written as: {a.also_called.join(', ')}</p>
                    </div>
                  ))}
                </div>
              ) : <p className="text-sm text-muted">No allergies recorded.</p>}
              {c.diets.map((d) => (
                <div key={d.diet}>
                  <p className="text-xs font-semibold uppercase tracking-wider text-muted">{d.diet} diet</p>
                  <ul className="mt-1 space-y-0.5 text-sm">{d.notes.map((n, i) => <li key={i}>{n}</li>)}</ul>
                </div>
              ))}
              {c.conditions.length > 0 && (
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-muted">Health notes</p>
                  <p className="mt-1 text-sm capitalize">{c.conditions.join(', ')}</p>
                  <p className="text-xs text-muted">Daily limits: sugar {c.limits.sugar_g_per_day} g · sodium {c.limits.sodium_mg_per_day} mg</p>
                </div>
              )}
              {c.avoid.length > 0 && (
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-muted">Prefers to avoid</p>
                  <p className="mt-1 text-sm">{c.avoid.join(', ')}</p>
                </div>
              )}
            </div>
          </article>
        ))}
      </div>
    </div>
  )
}
