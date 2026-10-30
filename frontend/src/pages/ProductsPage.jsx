import { useEffect, useState } from 'react'
import { api } from '../api/client.js'
import { Empty, ErrorBox, Spinner } from '../components/Feedback.jsx'
import { IconCart, IconCheck } from '../components/Icons.jsx'
import ScoreBadge from '../components/ScoreBadge.jsx'
import Section from '../components/Section.jsx'
import StatusPill from '../components/StatusPill.jsx'
import { useApp } from '../context/AppContext.jsx'

const nice = (s) => s.replace(/_/g, ' ')

export default function ProductsPage() {
  const { member } = useApp()
  const [filters, setFilters] = useState({ category: '', q: '', safe_only: false, sort: 'score' })
  const [state, setState] = useState({ loading: true, data: null, error: null })
  const [open, setOpen] = useState(null)
  const [listed, setListed] = useState({})

  useEffect(() => {
    let alive = true
    setState((s) => ({ ...s, loading: true, error: null }))
    const t = setTimeout(() => {
      api.products({ ...filters, member })
        .then((data) => alive && setState({ loading: false, data, error: null }))
        .catch((error) => alive && setState({ loading: false, data: null, error }))
    }, 200)
    return () => { alive = false; clearTimeout(t) }
  }, [filters, member])

  const set = (k, v) => setFilters((f) => ({ ...f, [k]: v }))
  const add = async (p) => {
    await api.shoppingAdd({ product_name: p.product_name, brand: p.brand, code: p.code, score: p.score })
    setListed((l) => ({ ...l, [p.code]: true }))
  }
  const d = state.data

  return (
    <div className="space-y-6">
      <Section title="Product explorer" subtitle="Indian packaged foods scored with the same formula, checked against your family's profile. No AI.">
        <div className="grid gap-3 sm:grid-cols-4">
          <label className="block sm:col-span-2"><span className="label">Search</span>
            <input className="input" placeholder="e.g. oats, Britannia, chips" value={filters.q} onChange={(e) => set('q', e.target.value)} />
          </label>
          <label className="block"><span className="label">Category</span>
            <select className="input" value={filters.category} onChange={(e) => set('category', e.target.value)}>
              <option value="">All categories</option>
              {d?.categories?.map((c) => <option key={c} value={c}>{nice(c)}</option>)}
            </select>
          </label>
          <label className="block"><span className="label">Sort by</span>
            <select className="input" value={filters.sort} onChange={(e) => set('sort', e.target.value)}>
              <option value="score">Best score</option>
              <option value="sugar">Least sugar</option>
              <option value="sodium">Least sodium</option>
              <option value="protein">Most protein</option>
              <option value="price">Lowest price</option>
            </select>
          </label>
        </div>
        <label className="mt-3 inline-flex cursor-pointer items-center gap-2 text-sm">
          <input type="checkbox" className="h-4 w-4 accent-[rgb(var(--brand))]" checked={filters.safe_only} onChange={(e) => set('safe_only', e.target.checked)} />
          Hide products that are unsafe for {member === 'all' ? 'anyone in my family' : member}
        </label>
      </Section>

      {state.loading && !d && <Spinner />}
      <ErrorBox error={state.error} />
      {d && (
        <>
          <p className="text-sm text-muted">{d.count} products · {d.note}</p>
          {d.count === 0 && <Empty title="No products match these filters" />}
          <div className="grid gap-4 md:grid-cols-2">
            {d.products.map((p) => (
              <div key={p.code} className="card p-4 sm:p-5">
                <div className="flex gap-4">
                  <ScoreBadge score={p.score} color={p.color} size="sm" />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="font-semibold leading-snug">{p.product_name}</p>
                        <p className="text-xs capitalize text-muted">{p.brand} · {nice(p.category)}{p.price_inr ? ` · ~₹${p.price_inr}` : ''}</p>
                      </div>
                      <StatusPill status={p.status} small />
                    </div>
                    <div className="mt-2 grid grid-cols-4 gap-1 text-center text-[11px]">
                      <Nut label="Sugar" v={p.sugar_g} u="g" />
                      <Nut label="Sodium" v={p.sodium_mg} u="mg" />
                      <Nut label="Sat fat" v={p.sat_fat_g} u="g" />
                      <Nut label="Protein" v={p.protein_g} u="g" />
                    </div>
                    {p.members.filter((m) => m.status !== 'SAFE').slice(0, 2).map((m) => (
                      <p key={m.member} className="mt-1.5 text-xs text-muted"><b className="text-ink">{m.member}:</b> {m.reason}</p>
                    ))}
                    <div className="mt-3 flex flex-wrap gap-2">
                      <button className="btn-ghost px-3 py-1.5 text-xs" onClick={() => add(p)} disabled={listed[p.code]}>
                        {listed[p.code] ? <><IconCheck width={13} height={13} /> On your list</> : <><IconCart width={13} height={13} /> Add to list</>}
                      </button>
                      <button className="text-xs font-medium text-brand hover:underline" onClick={() => setOpen(open === p.code ? null : p.code)}>
                        {open === p.code ? 'Hide ingredients' : 'Ingredients'}
                      </button>
                    </div>
                    {open === p.code && <p className="mt-2 text-xs leading-relaxed text-muted">{p.ingredients.join(', ')}</p>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

function Nut({ label, v, u }) {
  return (
    <div className="rounded-lg bg-surface px-1 py-1.5">
      <p className="text-muted">{label}</p>
      <p className="font-semibold text-ink">{v == null ? '–' : `${v}${u === 'mg' ? '' : ''}`}<span className="font-normal text-muted"> {v == null ? '' : u}</span></p>
    </div>
  )
}
