import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client.js'
import { ErrorBox, Spinner } from '../components/Feedback.jsx'
import { IconPrint, IconShare, IconSpeaker } from '../components/Icons.jsx'
import ScoreBadge from '../components/ScoreBadge.jsx'
import Section from '../components/Section.jsx'
import { useApp } from '../context/AppContext.jsx'

const VOICE_LANG = { en: 'en-IN', hi: 'hi-IN', ta: 'ta-IN' }
const colorFor = (s) => (s >= 70 ? 'green' : s >= 50 ? 'amber' : 'red')

function speak(text, language) {
  if (!('speechSynthesis' in window)) return
  window.speechSynthesis.cancel()
  const u = new SpeechSynthesisUtterance(text)
  u.lang = VOICE_LANG[language] || 'en-IN'
  const voice = window.speechSynthesis.getVoices().find((v) => v.lang?.toLowerCase().startsWith(u.lang.slice(0, 2)))
  if (voice) u.voice = voice
  window.speechSynthesis.speak(u)
}

// Weekly family report: numbers computed by the app, write-up by the AI (one cached call).
export default function ReportPage() {
  const { language } = useApp()
  const [state, setState] = useState({ loading: true, data: null, error: null })

  const load = (refresh = false) => {
    setState((s) => ({ ...s, loading: true, error: null }))
    api.report(language, refresh)
      .then((data) => setState({ loading: false, data, error: null }))
      .catch((error) => setState({ loading: false, data: null, error }))
  }
  useEffect(() => load(), [language]) // eslint-disable-line react-hooks/exhaustive-deps

  if (state.loading && !state.data) return <div className="card"><Spinner label="Putting together your family's week..." /></div>
  if (state.error) return <ErrorBox error={state.error} onRetry={() => load()} />
  const { facts: f, report: r, source } = state.data
  const share = [
    `LabelGuard weekly report (${f.period})`, r.headline, r.summary,
    ...r.members.map((m) => `• ${m.name}: ${m.note}`),
    'Tips:', ...r.tips.map((t) => `- ${t}`),
  ].join('\n')

  return (
    <div className="space-y-6">
      <div className="no-print flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold tracking-tight">Weekly family report</h1>
          <p className="text-sm text-muted">{f.period} · language follows the sidebar setting</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="btn-ghost" onClick={() => speak(`${r.headline}. ${r.summary}`, language)}><IconSpeaker width={16} height={16} /> Listen</button>
          <a className="btn-ghost" target="_blank" rel="noreferrer" href={`https://wa.me/?text=${encodeURIComponent(share)}`}><IconShare width={16} height={16} /> WhatsApp</a>
          <button className="btn-primary" onClick={() => window.print()}><IconPrint width={16} height={16} /> Print / PDF</button>
        </div>
      </div>

      {/* AI write-up */}
      <section className="card bg-gradient-to-br from-brand-soft to-card">
        <p className="text-xs font-semibold uppercase tracking-wider text-brand">This week at a glance · {f.period}</p>
        <h2 className="mt-2 text-2xl font-bold tracking-tight" lang={language}>{r.headline}</h2>
        <p className="mt-3 max-w-3xl text-[15px] leading-relaxed text-ink/85" lang={language}>{r.summary}</p>
        <div className="no-print mt-4 flex flex-wrap items-center gap-3 text-[11px] text-muted">
          <span>
            {source === 'llm' && 'Written by AI from the numbers below'}
            {source === 'cache' && 'Written by AI from the numbers below · cached, 0 tokens'}
            {source === 'template_fallback' && 'Template summary (AI unavailable)'}
          </span>
          <button className="font-semibold text-brand hover:underline disabled:opacity-50" disabled={state.loading} onClick={() => load(true)}>
            {state.loading ? 'Rewriting...' : 'Rewrite'}
          </button>
        </div>
      </section>

      {/* Numbers (deterministic) */}
      <div className="grid gap-4 sm:grid-cols-4">
        <Stat label="Products scanned" value={f.products_scanned} />
        <Stat label="Average score" value={f.average_score != null ? `${f.average_score}/100` : '–'} />
        <Stat label="Items logged" value={f.items_logged} />
        <Stat label="Misleading claims caught" value={f.misleading_claims_caught} />
      </div>

      <Section title="Each family member" subtitle="Weekly budget = daily limit × 7, from logged packaged foods">
        <div className="grid gap-4 md:grid-cols-2">
          {f.members.map((m) => {
            const note = r.members.find((x) => x.name === m.name)?.note
            return (
              <div key={m.name} className="rounded-xl border border-line p-4">
                <div className="flex items-center justify-between">
                  <p className="font-semibold">{m.name}</p>
                  <span className="text-xs text-muted">{m.items_logged} item(s) logged</span>
                </div>
                <Budget label="Sugar" used={m.sugar_g} budget={m.sugar_budget_g} pct={m.sugar_pct} unit="g" />
                <Budget label="Sodium" used={m.sodium_mg} budget={m.sodium_budget_mg} pct={m.sodium_pct} unit="mg" />
                {note && <p className="mt-3 text-sm text-ink/85" lang={language}>{note}</p>}
                {m.scanned_products_unsuitable > 0 && (
                  <p className="mt-1.5 text-xs text-muted">{m.scanned_products_unsuitable} scanned product(s) this week were unsuitable for {m.name}.</p>
                )}
              </div>
            )
          })}
        </div>
      </Section>

      <div className="grid gap-6 lg:grid-cols-2">
        <Section title="Swaps that would help most" subtitle="For the lowest-scoring things eaten this week">
          {f.swaps.length ? (
            <ul className="space-y-3">
              {f.swaps.map((s) => (
                <li key={s.from} className="rounded-xl border border-line p-3.5">
                  <div className="flex items-center gap-3">
                    <ScoreBadge score={s.from_score} color={colorFor(s.from_score)} size="sm" />
                    <span className="text-muted">→</span>
                    <ScoreBadge score={s.to_score} color={colorFor(s.to_score)} size="sm" />
                    <p className="min-w-0 text-sm"><span className="text-muted line-through">{s.from}</span><br /><b>{s.to}</b></p>
                  </div>
                  <p className="mt-2 text-sm text-good-ink">{s.why}</p>
                  {s.impact && <p className="mt-1 text-xs text-muted">{s.impact}</p>}
                </li>
              ))}
            </ul>
          ) : <p className="text-sm text-muted">Log what your family eats (Scan → Log this) to get swap suggestions.</p>}
        </Section>
        <Section title="Tips for next week">
          <ol className="space-y-2.5">
            {r.tips.map((t, i) => (
              <li key={i} className="flex gap-3 text-sm" lang={language}>
                <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-brand-soft text-xs font-bold text-brand">{i + 1}</span>
                <span className="pt-0.5">{t}</span>
              </li>
            ))}
          </ol>
          {f.budget_alerts.length > 0 && (
            <div className="mt-4 rounded-xl border border-warn-line bg-warn-bg p-3 text-sm text-warn-ink">
              {f.budget_alerts.map((a, i) => <p key={i}>{a}</p>)}
            </div>
          )}
          <p className="no-print mt-4 text-xs text-muted">See details in <Link to="/tracker" className="text-brand hover:underline">Tracker</Link> and <Link to="/insights" className="text-brand hover:underline">Insights</Link>.</p>
        </Section>
      </div>
      <p className="text-xs text-muted">Informational only, not medical advice. Numbers cover packaged foods logged in LabelGuard, not your whole diet.</p>
    </div>
  )
}

function Stat({ label, value }) {
  return (
    <div className="card p-4 sm:p-5">
      <p className="text-xs font-semibold uppercase tracking-wider text-muted">{label}</p>
      <p className="mt-1 text-2xl font-extrabold tracking-tight">{value}</p>
    </div>
  )
}

function Budget({ label, used, budget, pct, unit }) {
  const bar = pct >= 100 ? 'bg-bad' : pct >= 50 ? 'bg-warn' : 'bg-good'
  return (
    <div className="mt-3">
      <div className="mb-1 flex justify-between text-xs">
        <span className="font-medium">{label}</span>
        <span className="text-muted">{used} / {budget} {unit} · <b className="text-ink">{pct}%</b></span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-surface">
        <div className={`h-full rounded-full ${bar}`} style={{ width: `${Math.min(100, pct)}%` }} />
      </div>
    </div>
  )
}
