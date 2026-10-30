import { useState } from 'react'
import { api } from '../api/client.js'
import { useApp } from '../context/AppContext.jsx'

// "Log this": records the product as eaten so weekly sugar/sodium budgets update.
export default function LogIntake({ scanId, servingG }) {
  const { household, member } = useApp()
  const [who, setWho] = useState(member !== 'all' ? member : household.members[0]?.name || '')
  const [servings, setServings] = useState(1)
  const [msg, setMsg] = useState(null)
  const [busy, setBusy] = useState(false)

  const submit = async () => {
    setBusy(true)
    setMsg(null)
    try {
      const r = await api.log(scanId, who, Number(servings))
      setMsg({ ok: true, week: r.member_week, grams: r.grams })
    } catch (e) {
      setMsg({ ok: false, text: e.detail || e.message })
    } finally {
      setBusy(false)
    }
  }

  if (!household.members.length) return null
  return (
    <div className="space-y-3">
      <div>
        <label className="label" htmlFor="log-who">Who ate it</label>
        <select id="log-who" className="input" value={who} onChange={(e) => setWho(e.target.value)}>
          {household.members.map((m) => <option key={m.name}>{m.name}</option>)}
        </select>
      </div>
      <div>
        <label className="label" htmlFor="log-serv">Servings · {servingG ? `${servingG} g each` : '100 g each'}</label>
        <div className="flex gap-2">
          <input id="log-serv" type="number" min="0.5" max="20" step="0.5" className="input" value={servings}
            onChange={(e) => setServings(e.target.value)} />
          <button className="btn-primary shrink-0" onClick={submit} disabled={busy || !who}>
            {busy ? 'Logging...' : 'Log this'}
          </button>
        </div>
      </div>
      {msg?.ok && (
        <div className="rounded-xl border border-good-line bg-good-bg p-3 text-sm">
          <p className="font-medium text-good-ink">Logged {msg.grams} g for {who}</p>
          <p className="mt-1 text-ink/80">This week: {msg.week.sugar_pct}% of sugar budget · {msg.week.sodium_pct}% of sodium budget</p>
          {msg.week.messages.map((t, i) => <p key={i} className="mt-1 font-semibold text-warn-ink">{t}</p>)}
        </div>
      )}
      {msg && !msg.ok && <p className="rounded-xl border border-bad-line bg-bad-bg p-3 text-sm text-bad-ink">{msg.text}</p>}
    </div>
  )
}
