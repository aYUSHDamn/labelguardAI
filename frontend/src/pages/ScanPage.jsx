import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../api/client.js'
import BarcodeEntry from '../components/BarcodeEntry.jsx'
import { ErrorBox, Spinner } from '../components/Feedback.jsx'
import { IconBarcode, IconEdit, IconPaste } from '../components/Icons.jsx'
import ImageCapture from '../components/ImageCapture.jsx'
import ManualEntry from '../components/ManualEntry.jsx'
import ResultView from '../components/ResultView.jsx'
import { useApp } from '../context/AppContext.jsx'
import { useAsync } from '../hooks/useAsync.js'

const MODES = [
  ['photo', 'Photo', IconPaste, '1 AI call'],
  ['barcode', 'Barcode', IconBarcode, '0 tokens'],
  ['manual', 'Type it in', IconEdit, '0 tokens'],
]

export default function ScanPage() {
  const { lastScan, setLastScan, profileSaved, household } = useApp()
  const [params, setParams] = useSearchParams()
  const [mode, setMode] = useState('photo')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const demos = useAsync(() => api.demoLabels(), [])

  // /?scan=12 opens a past scan, re-analysed with the current profile.
  const scanParam = params.get('scan')
  useEffect(() => {
    if (!scanParam) return
    setBusy(true)
    api.getScan(scanParam).then(setLastScan).catch(setError).finally(() => setBusy(false))
  }, [scanParam, setLastScan])

  const run = async (fn) => {
    setBusy(true)
    setError(null)
    try {
      const result = await fn()
      setLastScan(result)
      setParams({})
      setTimeout(() => document.getElementById('result')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50)
    } catch (e) {
      setError(e)
    } finally {
      setBusy(false)
    }
  }

  // Re-analyse the current scan when the profile changes (rules only, no AI).
  useEffect(() => {
    if (lastScan?.scan_id) api.getScan(lastScan.scan_id).then(setLastScan).catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [household])

  return (
    <div className="space-y-6">
      {!profileSaved && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-brand/20 bg-brand-soft px-5 py-4">
          <p className="text-sm">
            <span className="font-semibold text-brand">Set up your family first.</span>{' '}
            Describe allergies, diets and health goals once and every scan is checked against them.
          </p>
          <Link to="/profile" className="btn-primary py-2">Set up profile</Link>
        </div>
      )}

      <section className="card">
        <div className="mb-5">
          <h1 className="text-xl font-bold tracking-tight">Scan a food label</h1>
          <p className="mt-1 text-sm text-muted">
            Get a personal verdict for every family member, hidden sugars, misleading claims and better alternatives.
          </p>
        </div>

        <div className="mb-5 grid grid-cols-3 gap-1 rounded-xl bg-surface p-1" role="tablist">
          {MODES.map(([key, label, Icon, cost]) => (
            <button key={key} role="tab" aria-selected={mode === key} onClick={() => setMode(key)}
              className={`flex flex-col items-center gap-0.5 rounded-lg px-2 py-2 text-sm font-semibold transition sm:flex-row sm:justify-center sm:gap-2 ${
                mode === key ? 'bg-card text-ink shadow-sm' : 'text-muted hover:text-ink'}`}>
              <Icon width={16} height={16} />
              {label}
              <span className="text-[10px] font-medium text-muted">{cost}</span>
            </button>
          ))}
        </div>

        {mode === 'photo' && <ImageCapture busy={busy} active={mode === 'photo'} onSubmit={(files) => run(() => api.scanImage(files))} />}
        {mode === 'barcode' && <BarcodeEntry busy={busy} onSubmit={(code) => run(() => api.scanBarcode(code))} />}
        {mode === 'manual' && <ManualEntry busy={busy} onSubmit={(ex) => run(() => api.scanManual(ex))} />}

        <div className="mt-6">
          <p className="label">No label handy? Try a demo label</p>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            {demos.data?.map((d) => (
              <button key={d.key} disabled={busy} onClick={() => run(() => api.scanDemo(d.key))}
                className="rounded-xl border border-line bg-card px-3.5 py-3 text-left transition hover:border-brand/40 hover:bg-brand-soft/40 disabled:opacity-50">
                <span className="block text-sm font-semibold">{d.product_name.replace(' (demo label)', '')}</span>
                <span className="block text-xs capitalize text-muted">{d.category.replace(/_/g, ' ')}</span>
              </button>
            ))}
          </div>
        </div>
      </section>

      {busy && <BusyCard />}
      <ErrorBox error={error} />
      <div id="result" className="scroll-mt-4">
        {lastScan && !busy && <ResultView scan={lastScan} />}
      </div>
    </div>
  )
}

// Loading state that explains itself if the AI is slow (Google's models can be overloaded).
function BusyCard() {
  const [secs, setSecs] = useState(0)
  useEffect(() => {
    const t = setInterval(() => setSecs((x) => x + 1), 1000)
    return () => clearInterval(t)
  }, [])
  const label = secs < 8
    ? "Reading the label and checking it against your family's profile..."
    : secs < 25
      ? `The AI is busy right now, so we're trying a backup model... (${secs}s)`
      : `Still working (${secs}s). Google's AI is overloaded; demo labels and barcode lookup work instantly meanwhile.`
  return <div className="card"><Spinner label={label} /></div>
}
