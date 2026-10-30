import { useState } from 'react'
import { api } from '../api/client.js'
import Disclaimer from '../components/Disclaimer.jsx'
import { Spinner } from '../components/Feedback.jsx'
import Section from '../components/Section.jsx'
import { useAsync } from '../hooks/useAsync.js'

const PURPOSES = { profile_parse: 'Profile parsing', extraction: 'Label vision extraction', explanation: 'Short explanation', ask: 'Ask about product (optional)', report: 'Weekly report (optional)' }

export default function AboutPage() {
  const formula = useAsync(() => api.formula(), [])
  const stats = useAsync(() => api.stats(), [])
  const [resetMsg, setResetMsg] = useState(null)
  const reset = async () => {
    if (!window.confirm('Clear all scans, intake logs, feedback and the shopping list? Your family profile is kept.')) return
    await api.resetDemo()
    setResetMsg('Demo history cleared. Your family profile is kept.')
  }

  return (
    <div className="space-y-4">
      <Section title="How LabelGuard works">
        <p className="rounded-xl bg-brand/10 p-3 text-sm font-semibold">
          The LLM handles perception and interpretation. Deterministic Python rules and real databases handle anything
          that must be consistent, verifiable or cheap.
        </p>
        <div className="mt-3 grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <p className="label">Where the AI is (3 core calls + 1 optional)</p>
            <ol className="list-decimal space-y-1 pl-5">
              <li>Reading your profile text into structured fields, once per edit</li>
              <li>Reading the label photos (vision, up to 3 in one call), cached by image hash</li>
              <li>A 2-3 line summary in English / Hindi / Tamil, cached</li>
              <li>Optional: answering a typed question about a product, grounded in the rule results, cached</li>
              <li>Optional: writing the weekly family report from numbers the app computed, cached</li>
            </ol>
            <p className="mt-2 text-xs text-muted">Barcode lookup, manual entry, demo labels and every other module use zero tokens.</p>
          </div>
          <div>
            <p className="label">What is plain Python (0 tokens)</p>
            <ul className="list-disc space-y-1 pl-5">
              <li>Allergen, Jain / veg / vegan / halal and condition flags with evidence</li>
              <li>Hidden-sugar and INS additive lookup tables</li>
              <li>Claim checker (FSSAI thresholds) and per-serving check</li>
              <li>Health score, alternatives ranking, tracker, compare</li>
            </ul>
          </div>
        </div>
      </Section>

      <Section title="Health score formula" subtitle="Same input, same score, every time">
        {formula.loading && <Spinner />}
        {formula.data && (
          <>
            <table className="w-full text-sm">
              <thead><tr className="text-left text-xs uppercase text-muted"><th className="py-1">Component</th><th>Rule</th><th className="text-right">Max</th></tr></thead>
              <tbody>
                {formula.data.components.map((c) => (
                  <tr key={c.key} className="border-t border-line">
                    <td className="py-1.5 pr-2 font-semibold">{c.label}</td>
                    <td className="py-1.5 pr-2 text-muted">{c.rule}</td>
                    <td className="py-1.5 text-right tabular-nums">{['fiber', 'protein'].includes(c.key) ? '+' : '-'}{c.max}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="mt-2 text-sm">Start at 100, apply the components, clamp to 0-100. Grades: 70+ Good choice, 50-69 Okay occasionally, below 50 Limit this.</p>
            <details className="mt-2 text-xs text-muted"><summary className="cursor-pointer">Full formula text</summary><pre className="mt-2 whitespace-pre-wrap">{formula.data.text}</pre></details>
          </>
        )}
      </Section>

      <Section title="AI usage so far" subtitle="Logged on the server for every call">
        {stats.loading && <Spinner />}
        {stats.data && (
          <>
            <p className="text-sm text-muted">Model: <code>{stats.data.model}</code></p>
            {stats.data.llm_usage.length === 0 ? (
              <p className="mt-2 text-sm text-muted">No AI calls yet (demo labels and the rules engine use none).</p>
            ) : (
              <table className="mt-2 w-full text-sm">
                <thead><tr className="text-left text-xs uppercase text-muted"><th>Purpose</th><th className="text-right">Calls</th><th className="text-right">Input tok</th><th className="text-right">Output tok</th><th className="text-right">Avg ms</th></tr></thead>
                <tbody>
                  {stats.data.llm_usage.map((u) => (
                    <tr key={u.purpose} className="border-t border-line">
                      <td className="py-1">{PURPOSES[u.purpose] || u.purpose}</td>
                      <td className="text-right tabular-nums">{u.ok_calls}/{u.calls}</td>
                      <td className="text-right tabular-nums">{u.input_tokens}</td>
                      <td className="text-right tabular-nums">{u.output_tokens}</td>
                      <td className="text-right tabular-nums">{u.avg_latency_ms ?? '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            <p className="mt-3 text-sm">
              Lookup tables: {stats.data.tables.sugar_aliases} sugar aliases, {stats.data.tables.additives} additives,
              {' '}{stats.data.tables.allergens} allergens, {stats.data.tables.diet_rules} diet rules, {stats.data.tables.fallback_products} fallback products.
            </p>
          </>
        )}
      </Section>

      <Section title="Evaluation" subtitle="Run from /backend/eval (see README)">
        <ul className="list-disc space-y-1 pl-5 text-sm">
          <li>Ingredient extraction accuracy vs hand-written ground truth</li>
          <li>Hidden-sugar and allergen precision / recall</li>
          <li>Claim-check accuracy</li>
          <li>Consistency over 3 repeated runs: rules output identical; extraction variance reported</li>
          <li>Degraded photos (blur, rotation, low light) and the accuracy drop</li>
          <li>Profile parser field accuracy on 10 sample profiles (AI vs keyword baseline)</li>
        </ul>
        <p className="mt-2 text-sm text-muted">Results are written to <code>backend/eval/results/summary.md</code> for your slides.</p>
      </Section>

      <Section title="Demo tools" subtitle="Start your viva with a clean history">
        <button className="btn-ghost text-bad-ink" onClick={reset}>Reset demo data</button>
        {resetMsg && <p className="mt-2 text-sm text-good-ink">{resetMsg}</p>}
      </Section>

      <Section title="Disclaimer"><Disclaimer /></Section>
    </div>
  )
}
