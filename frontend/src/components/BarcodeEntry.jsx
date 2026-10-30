import { useState } from 'react'
import { IconBarcode } from './Icons.jsx'

const EXAMPLES = [
  ['3017620422003', 'Nutella'],
  ['5449000000996', 'Coca-Cola'],
  ['7622210449283', 'Prince biscuits'],
]

// Type the number under the barcode -> Open Food Facts -> full analysis with ZERO AI tokens.
export default function BarcodeEntry({ onSubmit, busy }) {
  const [code, setCode] = useState('')
  const digits = code.replace(/\D/g, '')
  const valid = digits.length >= 8 && digits.length <= 14
  return (
    <div className="rounded-2xl border border-line bg-surface/60 p-5">
      <div className="flex items-start gap-3">
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-brand-soft text-brand"><IconBarcode /></span>
        <div>
          <p className="font-semibold">Look up by barcode</p>
          <p className="text-sm text-muted">Type the 8-13 digit number under the barcode. Data comes from Open Food Facts, so it costs zero AI tokens.</p>
        </div>
      </div>
      <form className="mt-4 flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); if (valid) onSubmit(digits) }}>
        <input className="input max-w-xs font-mono tracking-wider" inputMode="numeric" placeholder="e.g. 8901063010710"
          value={code} onChange={(e) => setCode(e.target.value)} aria-label="Barcode number" />
        <button className="btn-primary" type="submit" disabled={!valid || busy}>{busy ? 'Looking up...' : 'Look up'}</button>
      </form>
      <p className="mt-3 text-xs text-muted">
        Try:{' '}
        {EXAMPLES.map(([c, n], i) => (
          <span key={c}>
            <button type="button" className="font-medium text-brand hover:underline" onClick={() => setCode(c)}>{n} ({c})</button>
            {i < EXAMPLES.length - 1 ? ' · ' : ''}
          </span>
        ))}
      </p>
    </div>
  )
}
