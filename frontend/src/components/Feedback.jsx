// Small shared states: loading spinner, friendly error box, empty state.
import { IconAlert } from './Icons.jsx'

export function Spinner({ label = 'Loading...' }) {
  return (
    <div className="flex items-center gap-3 py-6 text-sm text-muted" role="status">
      <span className="h-5 w-5 animate-spin rounded-full border-2 border-line border-t-brand" />
      {label}
    </div>
  )
}

export function ErrorBox({ error, onRetry }) {
  if (!error) return null
  return (
    <div className="flex items-start gap-3 rounded-xl border border-bad-line bg-bad-bg p-4 text-sm" role="alert">
      <IconAlert className="mt-0.5 shrink-0 text-bad" />
      <div className="flex-1">
        <p className="font-semibold text-bad-ink">Something went wrong</p>
        <p className="text-ink/80">{error.detail || error.message || String(error)}</p>
      </div>
      {onRetry && (
        <button className="btn-ghost px-3 py-1.5" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  )
}

export function Empty({ title, children }) {
  return (
    <div className="rounded-xl border border-dashed border-line bg-surface/60 p-8 text-center text-sm text-muted">
      <p className="font-semibold text-ink">{title}</p>
      {children && <div className="mt-1">{children}</div>}
    </div>
  )
}
