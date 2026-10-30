import { useState } from 'react'
import { api } from '../api/client.js'
import { useApp } from '../context/AppContext.jsx'

// "Ask about this product": answered only from the label + rule results (cached; rules fallback).
export default function AskBox({ scanId, members }) {
  const { language } = useApp()
  const [q, setQ] = useState('')
  const [history, setHistory] = useState([])
  const [busy, setBusy] = useState(false)
  const kid = members.find((m) => ['son', 'daughter', 'child'].includes((m.relation || '').toLowerCase()))
  const suggestions = [
    kid ? `Can ${kid.member} have this after school?` : 'Is this okay as an everyday snack?',
    'Why is the score low?',
    'Which ingredients are the problem?',
    'How many servings a week is reasonable?',
  ]

  const ask = async (question) => {
    if (!question.trim()) return
    setBusy(true)
    try {
      const r = await api.ask(scanId, question, language)
      setHistory((h) => [{ q: question, a: r.answer, source: r.source }, ...h])
      setQ('')
    } catch (e) {
      setHistory((h) => [{ q: question, a: e.detail || 'Could not answer right now.', source: 'error' }, ...h])
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); ask(q) }}>
        <input className="input" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Ask anything about this product..." maxLength={300} />
        <button className="btn-primary shrink-0" disabled={busy || q.trim().length < 2}>{busy ? 'Thinking...' : 'Ask'}</button>
      </form>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm">
        <span className="text-muted">Try:</span>
        {suggestions.map((s) => (
          <button key={s} type="button" className="text-brand hover:underline disabled:opacity-50" disabled={busy} onClick={() => ask(s)}>{s}</button>
        ))}
      </div>
      {history.length > 0 && (
        <ul className="mt-4 space-y-3">
          {history.map((h, i) => (
            <li key={i} className="rounded-xl border border-line p-3.5">
              <p className="text-sm font-semibold">{h.q}</p>
              <p className="mt-1 text-sm leading-relaxed text-ink/85" lang={language}>{h.a}</p>
              <p className="mt-1.5 text-[11px] text-muted">
                {h.source === 'llm' && 'AI answer, grounded in this label\'s rule results'}
                {h.source === 'cache' && 'Cached answer (0 tokens)'}
                {h.source === 'rules_fallback' && 'Answer from the rules engine (AI unavailable)'}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
