import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client.js'
import { useApp } from '../context/AppContext.jsx'
import { IconCart, IconCheck, IconShare, IconTrash } from './Icons.jsx'

// Quick actions for a result: share (WhatsApp / copy), add to shopping list, delete.
export default function ResultActions({ scan }) {
  const { setLastScan } = useApp()
  const navigate = useNavigate()
  const [msg, setMsg] = useState(null)
  const a = scan.analysis
  const ex = scan.extraction

  const shareText = [
    `LabelGuard check: ${ex.brand ? `${ex.brand} ` : ''}${ex.product_name || 'this product'}`,
    a.verdict,
    ...a.members.map((m) => `• ${m.summary}`),
    a.hidden_sugars.length >= 2 ? `Sugar appears under ${a.hidden_sugars.length} names: ${a.hidden_sugars.map((h) => h.alias).join(', ')}` : null,
    '(Informational only, not medical advice)',
  ].filter(Boolean).join('\n')

  const flash = (t) => {
    setMsg(t)
    setTimeout(() => setMsg(null), 2500)
  }
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(shareText)
      flash('Copied summary to clipboard')
    } catch {
      flash('Copy blocked by the browser')
    }
  }
  const addToList = async () => {
    await api.shoppingAdd({ product_name: ex.product_name || 'Scanned product', brand: ex.brand, code: ex.barcode || `scan-${scan.scan_id}`, score: a.score.score, note: a.verdict })
    flash('Added to shopping list')
  }
  const remove = async () => {
    if (!window.confirm('Delete this scan and its intake logs?')) return
    await api.deleteScan(scan.scan_id)
    setLastScan(null)
    navigate('/')
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <a className="btn-ghost px-3 py-1.5 text-xs" target="_blank" rel="noreferrer"
        href={`https://wa.me/?text=${encodeURIComponent(shareText)}`}>
        <IconShare width={14} height={14} /> WhatsApp
      </a>
      <button className="btn-ghost px-3 py-1.5 text-xs" onClick={copy}>Copy summary</button>
      <button className="btn-ghost px-3 py-1.5 text-xs" onClick={addToList}><IconCart width={14} height={14} /> Add to list</button>
      <button className="btn-ghost px-3 py-1.5 text-xs text-bad-ink" onClick={remove}><IconTrash width={14} height={14} /> Delete</button>
      {msg && <span className="inline-flex items-center gap-1 text-xs font-medium text-good-ink"><IconCheck width={13} height={13} /> {msg}</span>}
    </div>
  )
}
