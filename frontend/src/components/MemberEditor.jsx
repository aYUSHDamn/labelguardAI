import { useState } from 'react'
import { IconTrash } from './Icons.jsx'

const DIETS = ['vegetarian', 'eggetarian', 'vegan', 'jain']
const DIET_LABELS = { vegetarian: 'Vegetarian', eggetarian: 'Eggetarian (veg + eggs)', vegan: 'Vegan', jain: 'Jain (no onion, garlic, roots)' }
const CONDITIONS = ['diabetes', 'prediabetes', 'hypertension', 'high_cholesterol', 'heart_disease',
  'lactose_intolerance', 'celiac', 'kidney_disease', 'pregnancy', 'obesity', 'pcos']

const toList = (s) => s.split(',').map((x) => x.trim()).filter(Boolean)
const nice = (s) => s.replace(/_/g, ' ')

// One household member: a compact summary card that expands into the editable form.
export default function MemberEditor({ m, onChange, onRemove, canRemove, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)
  const set = (k, v) => onChange({ ...m, [k]: v })
  const toggle = (k, v) => set(k, m[k].includes(v) ? m[k].filter((x) => x !== v) : [...m[k], v])
  const mainDiet = m.diet_rules.find((d) => DIETS.includes(d)) || ''
  const setMainDiet = (d) => set('diet_rules', [...(d ? [d] : []), ...m.diet_rules.filter((x) => !DIETS.includes(x))])
  const setLimit = (k, v) => onChange({ ...m, limits: { ...m.limits, [k]: v === '' ? null : Number(v) } })
  const tags = [
    ...m.allergens.map((a) => ['bad', `Allergy: ${a}`]),
    ...m.diet_rules.map((d) => ['brand', d]),
    ...m.conditions.map((c) => ['warn', nice(c)]),
    ...m.avoid_ingredients.map((x) => ['muted', `Avoids ${x}`]),
  ]
  const tagCls = { bad: 'bg-bad-bg text-bad-ink', brand: 'bg-brand-soft text-brand', warn: 'bg-warn-bg text-warn-ink', muted: 'bg-surface text-muted' }

  return (
    <div className="rounded-xl border border-line">
      <div className="flex items-start gap-3 p-4">
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-brand-soft text-sm font-bold text-brand">
          {(m.name || '?').slice(0, 2).toUpperCase()}
        </span>
        <div className="min-w-0 flex-1">
          <p className="font-semibold">
            {m.name || 'Unnamed'} <span className="text-sm font-normal capitalize text-muted">· {m.relation}{m.age ? `, ${m.age} yrs` : ''}</span>
          </p>
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {tags.length ? tags.map(([k, t], i) => (
              <span key={i} className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${tagCls[k]}`}>{t}</span>
            )) : <span className="text-xs text-muted">No restrictions set</span>}
          </div>
        </div>
        <button className="btn-ghost px-3 py-1.5" onClick={() => setOpen(!open)}>{open ? 'Done' : 'Edit'}</button>
      </div>

      {open && (
        <div className="space-y-4 border-t border-line p-4">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <Field label="Name"><input className="input" value={m.name} onChange={(e) => set('name', e.target.value)} /></Field>
            <Field label="Relation"><input className="input" value={m.relation} onChange={(e) => set('relation', e.target.value)} /></Field>
            <Field label="Age"><input className="input" type="number" min="0" max="119" value={m.age ?? ''} placeholder="Optional"
              onChange={(e) => set('age', e.target.value === '' ? null : Number(e.target.value))} /></Field>
          </div>

          <Field label="Allergies">
            <ListInput value={m.allergens} onChange={(v) => set('allergens', v)} placeholder="e.g. cashew, peanut (comma separated)" />
          </Field>

          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Diet">
              <select className="input" value={mainDiet} onChange={(e) => setMainDiet(e.target.value)}>
                <option value="">No restriction</option>
                {DIETS.map((d) => <option key={d} value={d}>{DIET_LABELS[d]}</option>)}
              </select>
            </Field>
            <div className="flex items-end">
              <Check checked={m.diet_rules.includes('halal')} onChange={() => toggle('diet_rules', 'halal')}
                label="Halal only" hint="Flags pork, alcohol, unclear gelatin" />
            </div>
          </div>

          <div>
            <span className="label">Health conditions</span>
            <div className="grid gap-x-4 gap-y-1 rounded-xl border border-line p-3 sm:grid-cols-2 lg:grid-cols-3">
              {[...CONDITIONS, ...m.conditions.filter((c) => !CONDITIONS.includes(c))].map((c) => (
                <Check key={c} checked={m.conditions.includes(c)} onChange={() => toggle('conditions', c)} label={nice(c)} />
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <Field label="Sugar limit (g/day)"><input className="input" type="number" min="1" value={m.limits.sugar_g_per_day ?? ''}
              onChange={(e) => setLimit('sugar_g_per_day', e.target.value)} /></Field>
            <Field label="Sodium limit (mg/day)"><input className="input" type="number" min="1" value={m.limits.sodium_mg_per_day ?? ''}
              onChange={(e) => setLimit('sodium_mg_per_day', e.target.value)} /></Field>
            <Field label="Sat. fat limit (g/day)"><input className="input" type="number" min="1" value={m.limits.sat_fat_g_per_day ?? ''}
              onChange={(e) => setLimit('sat_fat_g_per_day', e.target.value)} /></Field>
          </div>

          <Field label="Other ingredients to avoid">
            <ListInput value={m.avoid_ingredients} onChange={(v) => set('avoid_ingredients', v)} placeholder="e.g. palm oil, maida (comma separated)" />
          </Field>
          <Field label="Notes"><input className="input" value={m.notes} placeholder="Optional" onChange={(e) => set('notes', e.target.value)} /></Field>

          {canRemove && (
            <button className="inline-flex items-center gap-1.5 text-sm font-medium text-bad-ink hover:underline" onClick={onRemove}>
              <IconTrash width={14} height={14} /> Remove {m.name || 'member'}
            </button>
          )}
        </div>
      )}
    </div>
  )
}

function Field({ label, children }) {
  return <label className="block"><span className="label">{label}</span>{children}</label>
}

function Check({ checked, onChange, label, hint }) {
  return (
    <label className="flex cursor-pointer items-start gap-2.5 rounded-lg px-1.5 py-1.5 text-sm hover:bg-surface">
      <input type="checkbox" checked={checked} onChange={onChange}
        className="mt-0.5 h-4 w-4 shrink-0 rounded border-line accent-[rgb(var(--brand))]" />
      <span>
        <span className="capitalize">{label}</span>
        {hint && <span className="block text-xs text-muted">{hint}</span>}
      </span>
    </label>
  )
}

// Keeps the raw text while typing; commits the parsed list on blur.
function ListInput({ value, onChange, placeholder }) {
  return (
    <input className="input placeholder:italic placeholder:text-muted/60" defaultValue={value.join(', ')} key={value.join('|')}
      placeholder={placeholder} onBlur={(e) => onChange(toList(e.target.value))} />
  )
}
