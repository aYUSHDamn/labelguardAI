import { useState } from 'react'
import { api } from '../api/client.js'
import { Empty, ErrorBox, Spinner } from './Feedback.jsx'
import { IconCart, IconThumbDown, IconThumbUp } from './Icons.jsx'
import ScoreBadge from './ScoreBadge.jsx'

const DOWN_REASONS = [
  ['too_sweet', 'Too sweet'],
  ['too_expensive', 'Too expensive'],
  ['dont_like_brand', "Don't like brand"],
  ['not_available', 'Not available'],
]

// Real products from Open Food Facts or the local Indian products table, never invented by AI.
export default function AlternativesList({ result, loading, error, onRetry, onFeedback }) {
  if (loading) return <Spinner label="Finding better options..." />
  if (error) return <ErrorBox error={error} onRetry={onRetry} />
  if (!result) return null
  const { alternatives, base, considered, excluded, sources_used, note } = result
  return (
    <div>
      {alternatives.length === 0 ? (
        <Empty title="No better match found">
          Checked {considered} products: {excluded.not_better} didn't score higher than {base.score},{' '}
          {excluded.unsafe} conflicted with your family's profile.
        </Empty>
      ) : (
        <div className="space-y-3">
          {alternatives.map((a) => <AltCard key={a.code} a={a} scanId={result.scan_id} onFeedback={onFeedback} />)}
        </div>
      )}
      <p className="mt-3 text-xs text-muted">
        From {sources_used.map((s) => (s === 'fallback_db' ? 'our Indian products table' : 'Open Food Facts')).join(' + ') || 'no source'},
        scored with the same formula. {alternatives.some((a) => a.approximate) ? note : ''}
      </p>
    </div>
  )
}

function AltCard({ a, scanId, onFeedback }) {
  const [state, setState] = useState(null) // null | 'choose' | 'sent' | 'error'
  const [listed, setListed] = useState(false)
  const addToList = async () => {
    await api.shoppingAdd({ product_name: a.product_name, brand: a.brand, code: a.code, score: a.score, note: a.reason })
    setListed(true)
  }
  const send = async (vote, reason) => {
    try {
      await api.feedback({ scan_id: scanId, product_code: a.code, product_name: a.product_name, brand: a.brand, vote, reason })
      setState('sent')
      onFeedback && onFeedback()
    } catch {
      setState('error')
    }
  }
  return (
    <div className="flex gap-4 rounded-xl border border-line p-4 transition hover:border-brand/30">
      {a.image_url ? (
        <img src={a.image_url} alt="" className="h-14 w-14 shrink-0 rounded-lg object-cover" loading="lazy" />
      ) : (
        <ScoreBadge score={a.score} color={a.color} size="sm" />
      )}
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-baseline justify-between gap-x-3">
          <p className="font-semibold">{a.product_name}</p>
          {a.price_inr ? <span className="text-sm text-muted">~₹{a.price_inr}</span> : null}
        </div>
        <p className="text-xs text-muted">{a.brand} · {a.label}{a.approximate ? ' · approx. values' : ''}</p>
        <p className="mt-1.5 text-sm font-medium text-good-ink">{a.reason}</p>
        {a.swap_impact && <p className="mt-1 rounded-lg bg-good-bg px-2.5 py-1.5 text-xs text-good-ink">{a.swap_impact}</p>}
        {a.warnings.map((w, i) => (
          <p key={i} className="mt-0.5 text-xs text-warn-ink">Caution: {w}</p>
        ))}
        {a.feedback_note && <p className="mt-0.5 text-xs text-muted">Ranked using your feedback: {a.feedback_note}</p>}
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <button className="btn-ghost px-3 py-1.5 text-xs" onClick={addToList} disabled={listed}>
            <IconCart width={13} height={13} /> {listed ? 'On your list' : 'Add to list'}
          </button>
          {state === 'sent' && <span className="text-xs text-muted">Thanks! Future suggestions will use this.</span>}
          {state === 'error' && <span className="text-xs text-bad-ink">Couldn't save feedback.</span>}
          {state === null && (
            <>
              <button className="btn-ghost px-3 py-1.5 text-xs" onClick={() => send(1, 'tastes_good')}>
                <IconThumbUp width={13} height={13} /> Good pick
              </button>
              <button className="btn-ghost px-3 py-1.5 text-xs" onClick={() => setState('choose')}>
                <IconThumbDown width={13} height={13} /> Not for me
              </button>
            </>
          )}
          {state === 'choose' && (
            <>
              <select className="input w-auto py-1.5" defaultValue="" onChange={(e) => e.target.value && send(-1, e.target.value)}
                aria-label="Why is this not for you?">
                <option value="" disabled>Why not?</option>
                {DOWN_REASONS.map(([key, label]) => <option key={key} value={key}>{label}</option>)}
              </select>
              <button className="text-xs text-muted hover:underline" onClick={() => setState(null)}>Cancel</button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
