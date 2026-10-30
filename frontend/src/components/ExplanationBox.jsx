import { useEffect, useState } from 'react'
import { api } from '../api/client.js'
import { useApp } from '../context/AppContext.jsx'
import { IconSpeaker } from './Icons.jsx'

const VOICE_LANG = { en: 'en-IN', hi: 'hi-IN', ta: 'ta-IN' }

// Read the summary aloud with the browser's built-in speech (works offline, no tokens).
function speak(text, language) {
  if (!('speechSynthesis' in window)) return false
  window.speechSynthesis.cancel()
  const u = new SpeechSynthesisUtterance(text)
  u.lang = VOICE_LANG[language] || 'en-IN'
  const voice = window.speechSynthesis.getVoices().find((v) => v.lang?.toLowerCase().startsWith(u.lang.slice(0, 2)))
  if (voice) u.voice = voice
  u.rate = 0.95
  window.speechSynthesis.speak(u)
  return true
}

// The ONLY AI-written text on the result page: 2-3 lines, cached per scan/member/language on the server.
export default function ExplanationBox({ scanId }) {
  const { language, eli12, member } = useApp()
  const [state, setState] = useState({ loading: true, data: null, error: null })

  useEffect(() => {
    let alive = true
    setState({ loading: true, data: null, error: null })
    api
      .explain(scanId, language, eli12, member)
      .then((data) => alive && setState({ loading: false, data, error: null }))
      .catch((error) => alive && setState({ loading: false, data: null, error }))
    return () => {
      alive = false
    }
  }, [scanId, language, eli12, member])

  return (
    <div className="rounded-xl bg-brand-soft/70 p-4">
      <p className="text-xs font-semibold uppercase tracking-wider text-brand">
        What this means for {member === 'all' ? 'your family' : member}
      </p>
      {state.loading && (
        <div className="mt-2 space-y-2">
          <div className="h-3 w-11/12 animate-pulse rounded bg-brand/10" />
          <div className="h-3 w-3/4 animate-pulse rounded bg-brand/10" />
        </div>
      )}
      {state.error && <p className="mt-1.5 text-sm text-muted">Summary unavailable right now. The verdicts below are complete.</p>}
      {state.data && (
        <>
          <p className="mt-1.5 text-[15px] leading-relaxed" lang={language}>{state.data.explanation}</p>
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <button type="button" onClick={() => speak(state.data.explanation, language)}
              className="inline-flex items-center gap-1.5 rounded-lg bg-card px-2.5 py-1 text-xs font-semibold text-brand shadow-sm hover:brightness-95">
              <IconSpeaker width={14} height={14} /> Listen
            </button>
            <span className="text-[11px] text-muted">
              {state.data.source === 'template_fallback' ? 'Template summary (AI unavailable)' : 'AI summary of the rule results'}
              {state.data.source === 'cache' ? ' · cached' : ''}
            </span>
          </div>
        </>
      )}
    </div>
  )
}
