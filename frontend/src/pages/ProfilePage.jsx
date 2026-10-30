import { useEffect, useState } from 'react'
import { api } from '../api/client.js'
import { ErrorBox } from '../components/Feedback.jsx'
import { IconPlus } from '../components/Icons.jsx'
import MemberEditor from '../components/MemberEditor.jsx'
import Section from '../components/Section.jsx'
import { useApp } from '../context/AppContext.jsx'

const EXAMPLE = 'Pre-diabetic, allergic to cashews, Jain, cutting sodium. My son Rohan is 9 and lactose intolerant. My mother has high BP.'
const blank = (name = 'New member') => ({ name, relation: 'other', age: null, allergens: [], diet_rules: [], conditions: [],
  limits: { sugar_g_per_day: 25, sodium_mg_per_day: 2000, sat_fat_g_per_day: 20 }, avoid_ingredients: [], notes: '' })

export default function ProfilePage() {
  const { household, setHousehold, setProfileSaved, profileSaved } = useApp()
  const [text, setText] = useState('')
  const [draft, setDraft] = useState(null)
  const [parseInfo, setParseInfo] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (!draft && household.members.length) setDraft(structuredClone(household))
  }, [household, draft])

  const parse = async () => {
    setBusy(true)
    setError(null)
    try {
      const r = await api.parseProfile(text)
      setDraft(r.household)
      setParseInfo(r)
      setSaved(false)
    } catch (e) {
      setError(e)
    } finally {
      setBusy(false)
    }
  }

  const saveAll = async () => {
    setBusy(true)
    setError(null)
    try {
      const r = await api.saveProfile(draft, text || null)
      setHousehold(r.household)
      setDraft(structuredClone(r.household))
      setProfileSaved(true)
      setSaved(true)
    } catch (e) {
      setError(e)
    } finally {
      setBusy(false)
    }
  }

  const update = (i, m) => {
    setSaved(false)
    setDraft({ members: draft.members.map((x, j) => (j === i ? m : x)) })
  }

  return (
    <div className="space-y-4">
      <Section title="Describe your household" subtitle="Write it once in plain words. One AI call turns it into the form below, and every scan uses it.">
        <textarea className="input min-h-[96px] placeholder:italic placeholder:text-muted/60" value={text} onChange={(e) => setText(e.target.value)} placeholder={`e.g. ${EXAMPLE}`} />
        <div className="mt-2 flex flex-wrap gap-2">
          <button className="btn-primary" disabled={busy || text.trim().length < 3} onClick={parse}>{busy ? 'Reading...' : 'Fill the form from this'}</button>
          <button className="btn-ghost" onClick={() => setText(EXAMPLE)}>Use example</button>
        </div>
        {parseInfo && (
          <p className="mt-2 text-xs text-muted">
            {parseInfo.source === 'llm' && 'Parsed by AI. Check every field below, then save.'}
            {parseInfo.source === 'cache' && 'Same text as before: reused the saved parse (0 tokens). Check and save.'}
            {parseInfo.source === 'keyword_fallback' && parseInfo.warning}
          </p>
        )}
      </Section>

      <ErrorBox error={error} />

      {draft && (
        <Section title={`Household members (${draft.members.length})`} subtitle={profileSaved ? 'Saved profile. Edit and save again any time.' : 'Not saved yet.'}>
          <div className="space-y-3">
            {draft.members.map((m, i) => (
              <MemberEditor key={i} m={m} onChange={(nm) => update(i, nm)} canRemove={draft.members.length > 1}
                defaultOpen={/^Member \d+$/.test(m.name)}
                onRemove={() => setDraft({ members: draft.members.filter((_, j) => j !== i) })} />
            ))}
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <button className="btn-ghost" onClick={() => setDraft({ members: [...draft.members, blank(`Member ${draft.members.length + 1}`)] })}>
              <IconPlus width={16} height={16} /> Add member
            </button>
            <button className="btn-primary" disabled={busy} onClick={saveAll}>Save profile</button>
            {saved && <span className="text-sm font-semibold text-good">Saved. New scans will use this profile.</span>}
          </div>
        </Section>
      )}
    </div>
  )
}
