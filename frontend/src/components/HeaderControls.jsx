import { useApp } from '../context/AppContext.jsx'

// Global settings in the sidebar: who we check for, summary language, ELI12 mode.
export default function HeaderControls() {
  const { household, member, setMember, language, setLanguage, eli12, setEli12 } = useApp()
  return (
    <div className="space-y-3">
      <div>
        <label className="label" htmlFor="member-select">Checking for</label>
        <select id="member-select" className="input py-2" value={member} onChange={(e) => setMember(e.target.value)}>
          <option value="all">Whole family</option>
          {household.members.map((m) => (
            <option key={m.name} value={m.name}>{m.name}</option>
          ))}
        </select>
      </div>
      <div>
        <label className="label" htmlFor="lang-select">Summary language</label>
        <select id="lang-select" className="input py-2" value={language} onChange={(e) => setLanguage(e.target.value)}>
          <option value="en">English</option>
          <option value="hi">हिन्दी (Hindi)</option>
          <option value="ta">தமிழ் (Tamil)</option>
        </select>
      </div>
      <label className="flex cursor-pointer items-center justify-between gap-3 text-sm">
        <span>
          <span className="block font-medium">Explain like I'm 12</span>
          <span className="block text-xs text-muted">Simpler words in summaries</span>
        </span>
        <span className="relative inline-flex shrink-0">
          <input type="checkbox" className="peer sr-only" checked={eli12} onChange={(e) => setEli12(e.target.checked)} />
          <span className="h-6 w-11 rounded-full bg-line transition peer-checked:bg-brand" />
          <span className="absolute left-0.5 top-0.5 h-5 w-5 rounded-full bg-white shadow transition peer-checked:translate-x-5" />
        </span>
      </label>
    </div>
  )
}
