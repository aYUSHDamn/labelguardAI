import { useCallback, useEffect, useRef, useState } from 'react'
import { IconCamera, IconClose, IconPaste } from './Icons.jsx'

const MAX = 3

// Paste (Ctrl+V / button) or take photos of ONE pack - up to 3 (front, ingredients, nutrition).
// All photos go to the AI in a single call. The server resizes each to <= 1024 px.
export default function ImageCapture({ onSubmit, busy, active = true }) {
  const cameraRef = useRef(null)
  const [items, setItems] = useState([]) // [{file, url}]
  const [hint, setHint] = useState(null)

  useEffect(() => () => items.forEach((i) => URL.revokeObjectURL(i.url)), []) // eslint-disable-line

  const addImage = useCallback((blob, name = 'pasted-label.png') => {
    const file = blob instanceof File ? blob : new File([blob], name, { type: blob.type || 'image/png' })
    setItems((prev) => {
      if (prev.length >= MAX) {
        setHint(`Up to ${MAX} photos per product. Remove one to add another.`)
        return prev
      }
      setHint(null)
      return [...prev, { file, url: URL.createObjectURL(file) }]
    })
  }, [])

  useEffect(() => {
    if (!active) return undefined
    const onPaste = (e) => {
      const item = [...(e.clipboardData?.items || [])].find((i) => i.type.startsWith('image/'))
      if (!item) return
      e.preventDefault()
      addImage(item.getAsFile())
    }
    window.addEventListener('paste', onPaste)
    return () => window.removeEventListener('paste', onPaste)
  }, [addImage, active])

  const pasteFromButton = async () => {
    if (!navigator.clipboard?.read) {
      setHint('Your browser blocks clipboard access here. Press Ctrl+V (Cmd+V on Mac) instead.')
      return
    }
    try {
      for (const item of await navigator.clipboard.read()) {
        const type = item.types.find((t) => t.startsWith('image/'))
        if (type) {
          addImage(await item.getType(type))
          return
        }
      }
      setHint('No image in the clipboard. Copy a label image first (right-click > Copy image, or take a screenshot).')
    } catch {
      setHint('Clipboard access was blocked. Press Ctrl+V (Cmd+V on Mac) to paste instead.')
    }
  }

  const pickFromCamera = (e) => {
    const f = e.target.files?.[0]
    if (f) addImage(f, f.name)
    e.target.value = ''
  }

  const remove = (idx) => setItems((prev) => prev.filter((_, i) => i !== idx))

  return (
    <div>
      <input ref={cameraRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={pickFromCamera} />
      {items.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-line bg-surface/60 px-6 py-10 text-center">
          <span className="grid h-12 w-12 place-items-center rounded-2xl bg-brand-soft text-brand">
            <IconPaste width={22} height={22} />
          </span>
          <p className="mt-3 text-base font-semibold">Paste a label image</p>
          <p className="mt-1 text-sm text-muted">
            Copy a photo of the pack, then press{' '}
            <kbd className="rounded-md border border-line bg-card px-1.5 py-0.5 text-xs font-semibold">Ctrl</kbd> +{' '}
            <kbd className="rounded-md border border-line bg-card px-1.5 py-0.5 text-xs font-semibold">V</kbd>.
            {' '}Add up to {MAX} photos (front, ingredients, nutrition).
          </p>
          <div className="mt-5 flex flex-wrap justify-center gap-2">
            <button className="btn-primary" onClick={pasteFromButton} disabled={busy}>
              <IconPaste width={16} height={16} /> Paste image
            </button>
            <button className="btn-ghost" onClick={() => cameraRef.current?.click()} disabled={busy}>
              <IconCamera width={16} height={16} /> Take photo
            </button>
          </div>
        </div>
      ) : (
        <div className="rounded-2xl border border-line bg-surface/60 p-4">
          <div className="flex flex-wrap gap-3">
            {items.map((it, i) => (
              <div key={it.url} className="relative">
                <img src={it.url} alt={`Label photo ${i + 1}`} className="h-32 w-32 rounded-xl border border-line bg-card object-contain" />
                <span className="absolute left-1.5 top-1.5 rounded-md bg-ink/70 px-1.5 text-[11px] font-semibold text-white">{i + 1}</span>
                <button onClick={() => remove(i)} disabled={busy} aria-label={`Remove photo ${i + 1}`}
                  className="absolute -right-2 -top-2 grid h-6 w-6 place-items-center rounded-full border border-line bg-card text-muted shadow-sm hover:text-bad-ink">
                  <IconClose width={12} height={12} />
                </button>
              </div>
            ))}
            {items.length < MAX && (
              <div className="flex h-32 w-32 flex-col items-center justify-center gap-1.5 rounded-xl border-2 border-dashed border-line text-center">
                <button className="text-xs font-semibold text-brand hover:underline" onClick={pasteFromButton} disabled={busy}>+ Paste another</button>
                <button className="text-xs font-semibold text-brand hover:underline" onClick={() => cameraRef.current?.click()} disabled={busy}>+ Take photo</button>
                <span className="text-[11px] text-muted">or Ctrl+V</span>
              </div>
            )}
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <button className="btn-primary" onClick={() => onSubmit(items.map((i) => i.file))} disabled={busy}>
              {busy ? 'Reading label...' : `Analyse ${items.length > 1 ? `these ${items.length} photos` : 'this label'}`}
            </button>
            <button className="btn-ghost" onClick={() => setItems([])} disabled={busy}>Clear</button>
            <span className="text-xs text-muted">{items.length > 1 ? 'All photos are read together in one AI call.' : ''}</span>
          </div>
        </div>
      )}
      {hint && <p className="mt-3 rounded-xl border border-warn-line bg-warn-bg px-3 py-2 text-sm text-warn-ink">{hint}</p>}
    </div>
  )
}
