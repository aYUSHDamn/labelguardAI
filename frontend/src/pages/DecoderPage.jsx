import { useState } from 'react'
import { api } from '../api/client.js'
import { Empty, ErrorBox } from '../components/Feedback.jsx'
import Section from '../components/Section.jsx'
import StatusPill from '../components/StatusPill.jsx'

const EXAMPLES = ['E471', 'maltodextrin', 'gelatin', 'INS 102', 'kaju', 'natural flavours', 'onion powder', 'aspartame', 'carmine', 'jaggery']
const TYPE_STYLE = {
  Additive: 'bg-brand-soft text-brand',
  'Hidden sugar': 'bg-warn-bg text-warn-ink',
  Allergen: 'bg-bad-bg text-bad-ink',
  'Diet rule': 'bg-good-bg text-good-ink',
}

// "What is this ingredient, and is it OK for my family?" Lookup tables + the real rules engine. No AI.
export default function DecoderPage() {
  const [q, setQ] = useState('')
  const [state, setState] = useState({ loading: false, data: null, error: null })

  const search = async (term) => {
    const t = (term ?? q).trim()
    if (t.length < 2) return
    setQ(t)
    setState({ loading: true, data: null, error: null })
    try {
      setState({ loading: false, data: await api.lookup(t), error: null })
    } catch (error) {
      setState({ loading: false, data: null, error })
    }
  }
  const d = state.data

  return (
    <div className="space-y-6">
      <Section title="Ingredient decoder" subtitle="Type an INS / E-number or an ingredient to see what it is and whether it suits each family member.">
        <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); search() }}>
          <input className="input" value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. E471, maltodextrin, gelatin" autoFocus />
          <button className="btn-primary shrink-0" disabled={state.loading || q.trim().length < 2}>{state.loading ? 'Checking...' : 'Decode'}</button>
        </form>
        <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-sm">
          <span className="text-muted">Try:</span>
          {EXAMPLES.map((x) => <button key={x} className="text-brand hover:underline" onClick={() => search(x)}>{x}</button>)}
        </div>
      </Section>

      <ErrorBox error={state.error} />
      {d && (
        <div className="grid gap-6 lg:grid-cols-5">
          <Section className="lg:col-span-3" title={`What is "${d.query}"?`}>
            {!d.found && <Empty title="Not in our tables">It isn't a flagged additive, sugar, allergen or diet-sensitive ingredient that we track. Your family check still runs on the right.</Empty>}
            <div className="space-y-3">
              {d.entries.map((e, i) => (
                <div key={i} className="rounded-xl border border-line p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${TYPE_STYLE[e.type] || 'bg-surface text-muted'}`}>{e.type}</span>
                    <span className="font-semibold">{e.title}</span>
                  </div>
                  <p className="mt-1 text-sm">{e.summary}</p>
                  <ul className="mt-1.5 space-y-0.5 text-xs text-muted">
                    {e.details.filter(Boolean).map((x, j) => <li key={j}>{x}</li>)}
                  </ul>
                </div>
              ))}
            </div>
          </Section>
          <Section className="lg:col-span-2" title="For your family" subtitle="If a product lists this ingredient">
            <div className="space-y-3">
              {d.family.map((m) => (
                <div key={m.member} className="rounded-xl border border-line p-3.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-semibold">{m.member}</span>
                    <StatusPill status={m.status} />
                  </div>
                  {m.reasons.length ? (
                    <ul className="mt-1.5 space-y-1 text-sm text-muted">{m.reasons.map((r, i) => <li key={i}>{r}</li>)}</ul>
                  ) : <p className="mt-1.5 text-sm text-muted">No conflict with {m.member}'s profile.</p>}
                </div>
              ))}
            </div>
          </Section>
        </div>
      )}
    </div>
  )
}
