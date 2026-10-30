import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client.js'
import { useApp } from '../context/AppContext.jsx'
import AdditiveCards from './AdditiveCards.jsx'
import AlternativesList from './AlternativesList.jsx'
import AskBox from './AskBox.jsx'
import ClaimCheck from './ClaimCheck.jsx'
import ExplanationBox from './ExplanationBox.jsx'
import FrontBackCheck from './FrontBackCheck.jsx'
import HiddenSugars from './HiddenSugars.jsx'
import { IconInfo } from './Icons.jsx'
import LogIntake from './LogIntake.jsx'
import MemberVerdicts from './MemberVerdicts.jsx'
import ScoreBadge from './ScoreBadge.jsx'
import ScoreBreakdown from './ScoreBreakdown.jsx'
import Section from './Section.jsx'
import ResultActions from './ResultActions.jsx'
import ServingTable from './ServingTable.jsx'
import TrafficLight from './TrafficLight.jsx'

const SOURCE_LABEL = {
  gemini_vision: 'Read by AI vision',
  'gemini_vision+open_food_facts': 'AI vision + Open Food Facts',
  open_food_facts: 'Open Food Facts (barcode)',
  manual: 'Manual entry',
  demo: 'Demo label',
}

export default function ResultView({ scan }) {
  const { member } = useApp()
  const { analysis: a, extraction: ex } = scan
  const [alts, setAlts] = useState({ loading: true, data: null, error: null })
  const [tab, setTab] = useState('sugars')

  const loadAlts = useCallback(() => {
    setAlts((s) => ({ ...s, loading: true, error: null }))
    api
      .alternatives(scan.scan_id, member)
      .then((data) => setAlts({ loading: false, data, error: null }))
      .catch((error) => setAlts({ loading: false, data: null, error }))
  }, [scan.scan_id, member])
  useEffect(loadAlts, [loadAlts])

  const misleading = a.claims.filter((c) => c.verdict === 'misleading').length
  const flaggedAdditives = a.additives.filter((x) => x.concern === 'high' || x.concern === 'medium').length
  const tabs = [
    ['sugars', 'Hidden sugars', a.hidden_sugars.length],
    ['additives', 'Additives', a.additives.length],
    ['claims', 'Claim check', a.claims.length],
    ['nutrition', 'Nutrition', null],
    ['ingredients', 'Ingredients', ex.ingredients.length],
    ['score', 'How the score works', null],
  ]

  return (
    <div className="space-y-6">
      {/* Summary */}
      <section className="card">
        <div className="flex flex-col gap-6 md:flex-row md:items-start">
          <ScoreBadge score={a.score.score} color={a.score.color} label={a.score.label} />
          <div className="min-w-0 flex-1">
            <p className="text-xs font-medium uppercase tracking-wider text-muted">
              {ex.brand || 'Unknown brand'} · {ex.category.replace(/_/g, ' ')}
            </p>
            <h2 className="mt-1 text-2xl font-bold tracking-tight">{ex.product_name || 'Unnamed product'}</h2>
            <p className="mt-2 text-[15px] text-ink/80">{a.verdict}</p>
            <div className="mt-3 flex flex-wrap gap-2 text-xs">
              <Stat label="Sugar sources" value={a.hidden_sugars.length} bad={a.hidden_sugars.length >= 2} />
              <Stat label="Flagged additives" value={flaggedAdditives} bad={flaggedAdditives > 0} />
              <Stat label="Misleading claims" value={misleading} bad={misleading > 0} />
              {(a.front_back || []).length > 0 && (
                <Stat label="Front-of-pack tricks" value={a.front_back.filter((x) => x.verdict === 'misleading').length}
                  bad={a.front_back.some((x) => x.verdict === 'misleading')} />
              )}
              <span className="rounded-full bg-surface px-2.5 py-1 text-muted">
                {SOURCE_LABEL[scan.source] || scan.source}
                {scan.cached && scan.source !== 'demo' ? ' · cached, 0 tokens' : ''} · {Math.round(ex.confidence * 100)}% confident
              </span>
            </div>
            <div className="mt-4"><ResultActions scan={scan} /></div>
            <div className="mt-5"><ExplanationBox scanId={scan.scan_id} /></div>
            {a.data_warnings.length > 0 && (
              <ul className="mt-4 space-y-1.5">
                {a.data_warnings.map((w, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-muted">
                    <IconInfo width={15} height={15} className="mt-0.5 shrink-0 text-warn" />
                    {w}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </section>

      {/* Front-of-pack traffic light */}
      {Object.values(ex.nutrition_per_100g).some((v) => v != null) && (
        <Section title="At a glance" subtitle="Traffic-light label: green low, amber medium, red high">
          <TrafficLight nutrition={ex.nutrition_per_100g} servingG={ex.serving_size_g} liquid={a.liquid} />
        </Section>
      )}

      {/* Front of pack vs back of pack */}
      <Section title="Front vs back of pack" subtitle="Do the pictures and promises on the front match the ingredient list?">
        <FrontBackCheck items={a.front_back || []} />
      </Section>

      {/* Family verdicts */}
      <Section title="For your family" subtitle="Checked against each person's allergies, diet, health conditions and limits">
        <MemberVerdicts members={a.members} selected={member} />
      </Section>

      <Section title="Ask about this product" subtitle="Answers use only this label and the rule results">
        <AskBox scanId={scan.scan_id} members={a.members} />
      </Section>

      {/* Alternatives + log */}
      <div className="grid gap-6 lg:grid-cols-3">
        <Section className="lg:col-span-2" title="Better alternatives" subtitle="Same category, safe for your family, higher score"
          right={<Link className="text-sm font-semibold text-brand hover:underline" to="/alternatives">See all</Link>}>
          <AlternativesList result={alts.data} loading={alts.loading} error={alts.error} onRetry={loadAlts} />
        </Section>
        <Section title="Log this" subtitle="Adds to the weekly sugar & sodium tracker">
          <LogIntake scanId={scan.scan_id} servingG={ex.serving_size_g} />
        </Section>
      </div>

      {/* Details in tabs */}
      <section className="card">
        <div className="-mx-1 mb-5 overflow-x-auto">
          <div className="flex min-w-max gap-1 border-b border-line px-1">
            {tabs.map(([key, label, count]) => (
              <button key={key} onClick={() => setTab(key)}
                className={`-mb-px border-b-2 px-3 pb-2.5 text-sm font-medium transition ${
                  tab === key ? 'border-brand text-brand' : 'border-transparent text-muted hover:text-ink'
                }`}>
                {label}
                {count != null && <span className="ml-1.5 rounded-full bg-surface px-1.5 py-0.5 text-[11px] text-muted">{count}</span>}
              </button>
            ))}
          </div>
        </div>
        {tab === 'sugars' && <HiddenSugars sugars={a.hidden_sugars} />}
        {tab === 'additives' && <AdditiveCards additives={a.additives} />}
        {tab === 'claims' && <ClaimCheck claims={a.claims} />}
        {tab === 'nutrition' && <ServingTable serving={a.serving} />}
        {tab === 'score' && <ScoreBreakdown score={a.score} />}
        {tab === 'ingredients' && (
          ex.ingredients.length ? (
            <>
              <ol className="grid gap-x-8 gap-y-1.5 text-sm sm:grid-cols-2">
                {ex.ingredients.map((ing, i) => (
                  <li key={i} className="flex gap-2"><span className="w-5 shrink-0 text-right text-muted">{i + 1}.</span>{ing}</li>
                ))}
              </ol>
              {ex.may_contain.length > 0 && <p className="mt-4 text-sm text-muted">May contain: {ex.may_contain.join(', ')}</p>}
            </>
          ) : <p className="text-sm text-muted">No ingredient list was found in this photo.</p>
        )}
      </section>
    </div>
  )
}

function Stat({ label, value, bad }) {
  return (
    <span className={`rounded-full border px-2.5 py-1 font-medium ${bad ? 'border-bad-line bg-bad-bg text-bad-ink' : 'border-good-line bg-good-bg text-good-ink'}`}>
      {value} {label.toLowerCase()}
    </span>
  )
}
