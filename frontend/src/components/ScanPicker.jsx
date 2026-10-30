// Dropdown of past scans (used by Alternatives and Compare).
export default function ScanPicker({ scans, value, onChange, label, id }) {
  return (
    <div className="min-w-0 flex-1">
      <label className="label" htmlFor={id}>{label}</label>
      <select id={id} className="input" value={value ?? ''} onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}>
        <option value="">Choose a scan...</option>
        {scans.map((s) => (
          <option key={s.id} value={s.id}>
            #{s.id} {s.product_name || 'Unnamed'} ({s.score}/100)
          </option>
        ))}
      </select>
    </div>
  )
}
