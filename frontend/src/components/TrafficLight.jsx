// UK-style front-of-pack "traffic light" label, computed from the label numbers.
// Colours by level per 100 g/ml; % of adult Reference Intake (RI) per serving when known.
const RI = { energy_kcal: 2000, fat_g: 70, sat_fat_g: 20, sugar_g: 90, salt_g: 6 }
const THRESH = { // [low max, high min] per 100 g (solids) / per 100 ml (drinks)
  fat_g: { solid: [3, 17.5], liquid: [1.5, 8.75] },
  sat_fat_g: { solid: [1.5, 5], liquid: [0.75, 2.5] },
  sugar_g: { solid: [5, 22.5], liquid: [2.5, 11.25] },
  salt_g: { solid: [0.3, 1.5], liquid: [0.3, 1.5] },
}
const STYLE = {
  low: 'bg-good-bg border-good-line text-good-ink',
  medium: 'bg-warn-bg border-warn-line text-warn-ink',
  high: 'bg-bad-bg border-bad-line text-bad-ink',
  none: 'bg-surface border-line text-muted',
}

export default function TrafficLight({ nutrition, servingG, liquid }) {
  const n = { ...nutrition, salt_g: nutrition.sodium_mg != null ? nutrition.sodium_mg * 2.5 / 1000 : null }
  const per = servingG ? servingG / 100 : 1
  const unit = liquid ? 'ml' : 'g'
  const tiles = [
    ['energy_kcal', 'Energy', 'kcal'], ['fat_g', 'Fat', 'g'], ['sat_fat_g', 'Saturates', 'g'],
    ['sugar_g', 'Sugars', 'g'], ['salt_g', 'Salt', 'g'],
  ]
  const level = (k, v) => {
    if (v == null || !THRESH[k]) return 'none'
    const [lo, hi] = THRESH[k][liquid ? 'liquid' : 'solid']
    return v > hi ? 'high' : v <= lo ? 'low' : 'medium'
  }
  return (
    <div>
      <p className="mb-2 text-xs text-muted">
        {servingG ? `Each ${servingG} ${unit} serving contains` : `Per 100 ${unit}`} · % of an adult's reference intake
      </p>
      <div className="grid grid-cols-5 gap-1.5 sm:gap-2">
        {tiles.map(([k, label, u]) => {
          const v100 = n[k]
          const v = v100 == null ? null : v100 * per
          const lv = k === 'energy_kcal' ? 'none' : level(k, v100)
          return (
            <div key={k} className={`flex flex-col items-center rounded-xl border px-1 py-2 text-center ${STYLE[lv]}`}>
              <span className="text-[11px] font-semibold uppercase tracking-wide">{label}</span>
              <span className="mt-0.5 text-base font-bold text-ink sm:text-lg">{v == null ? '–' : fmt(v)}</span>
              <span className="text-[11px] text-ink/70">{u}</span>
              <span className="mt-1 text-[11px] font-semibold">{v == null ? '' : `${Math.round((v / RI[k]) * 100)}%`}</span>
              {lv !== 'none' && <span className="mt-0.5 text-[10px] font-bold uppercase">{lv}</span>}
            </div>
          )
        })}
      </div>
    </div>
  )
}

const fmt = (v) => (v >= 100 ? Math.round(v) : v >= 10 ? v.toFixed(0) : v.toFixed(1))
