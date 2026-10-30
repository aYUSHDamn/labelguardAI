import { useState } from 'react'

const CATEGORIES = ['biscuits_cookies', 'chips_namkeen', 'instant_noodles', 'breakfast_cereals', 'chocolates_confectionery',
  'soft_drinks', 'juices', 'dairy_drinks', 'yogurt_curd', 'ice_cream', 'bread_bakery', 'sauces_ketchup', 'spreads_jams',
  'ready_to_eat', 'health_drinks', 'nutrition_bars', 'sweets_mithai', 'pickles_chutneys', 'dairy_products', 'other']
const NUTRIENTS = [
  ['energy_kcal', 'Energy (kcal)'], ['sugar_g', 'Total sugar (g)'], ['sodium_mg', 'Sodium (mg)'],
  ['sat_fat_g', 'Saturated fat (g)'], ['fat_g', 'Total fat (g)'], ['protein_g', 'Protein (g)'], ['fiber_g', 'Fibre (g)'],
]
const EXAMPLE = {
  product_name: 'Masala Peanuts', brand: 'Home Test', category: 'chips_namkeen',
  ingredients: 'Peanuts (60%), Gram flour (besan), Edible vegetable oil (palmolein), Salt, Red chilli powder, Spices, Garlic powder, Citric acid (INS 330)',
  claims: 'high protein, no added preservatives', serving: '30',
  n: { energy_kcal: '560', sugar_g: '3', sodium_mg: '750', sat_fat_g: '7', fat_g: '38', protein_g: '22', fiber_g: '6' },
}

// No photo and no AI? Type the label in; the same rules engine analyses it (zero tokens).
export default function ManualEntry({ onSubmit, busy }) {
  const [f, setF] = useState({ product_name: '', brand: '', category: 'other', ingredients: '', claims: '', serving: '', n: {} })
  const set = (k, v) => setF((s) => ({ ...s, [k]: v }))
  const setN = (k, v) => setF((s) => ({ ...s, n: { ...s.n, [k]: v } }))
  const num = (v) => (v === '' || v == null ? null : Number(v))

  const submit = (e) => {
    e.preventDefault()
    onSubmit({
      product_name: f.product_name || null, brand: f.brand || null, category: f.category,
      ingredients: f.ingredients, // the server splits on commas outside brackets
      claims: f.claims.split(',').map((s) => s.trim()).filter(Boolean),
      serving_size_g: num(f.serving), serving_size: f.serving ? `${f.serving} g` : null,
      nutrition_per_100g: Object.fromEntries(NUTRIENTS.map(([k]) => [k, num(f.n[k])])),
      confidence: 1,
    })
  }

  return (
    <form onSubmit={submit} className="space-y-4 rounded-2xl border border-line bg-surface/60 p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="font-semibold">Type the label in</p>
        <button type="button" className="text-sm font-medium text-brand hover:underline" onClick={() => setF(EXAMPLE)}>Fill an example</button>
      </div>
      <div className="grid gap-3 sm:grid-cols-3">
        <label className="block"><span className="label">Product name</span><input className="input" value={f.product_name} onChange={(e) => set('product_name', e.target.value)} /></label>
        <label className="block"><span className="label">Brand</span><input className="input" value={f.brand} onChange={(e) => set('brand', e.target.value)} /></label>
        <label className="block"><span className="label">Category</span>
          <select className="input" value={f.category} onChange={(e) => set('category', e.target.value)}>
            {CATEGORIES.map((c) => <option key={c} value={c}>{c.replace(/_/g, ' ')}</option>)}
          </select>
        </label>
      </div>
      <label className="block"><span className="label">Ingredients (as printed, comma separated)</span>
        <textarea className="input min-h-[80px]" value={f.ingredients} onChange={(e) => set('ingredients', e.target.value)}
          placeholder="Wheat flour, Sugar, Palm oil, Emulsifier (INS 471), Salt" />
      </label>
      <div>
        <span className="label">Nutrition per 100 g</span>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {NUTRIENTS.map(([k, l]) => (
            <label key={k} className="block"><span className="mb-1 block text-xs text-muted">{l}</span>
              <input className="input" type="number" step="any" min="0" value={f.n[k] ?? ''} onChange={(e) => setN(k, e.target.value)} />
            </label>
          ))}
          <label className="block"><span className="mb-1 block text-xs text-muted">Serving size (g)</span>
            <input className="input" type="number" step="any" min="0" value={f.serving} onChange={(e) => set('serving', e.target.value)} />
          </label>
        </div>
      </div>
      <label className="block"><span className="label">Front-of-pack claims (optional, comma separated)</span>
        <input className="input" value={f.claims} onChange={(e) => set('claims', e.target.value)} placeholder="e.g. no added sugar, high fibre" />
      </label>
      <button className="btn-primary" disabled={busy || (!f.ingredients.trim() && !Object.values(f.n).some((v) => v !== ''))}>
        {busy ? 'Analysing...' : 'Analyse'}
      </button>
    </form>
  )
}
