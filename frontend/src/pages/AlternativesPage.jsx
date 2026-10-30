import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client.js'
import AlternativesList from '../components/AlternativesList.jsx'
import { Empty, ErrorBox, Spinner } from '../components/Feedback.jsx'
import ScanPicker from '../components/ScanPicker.jsx'
import Section from '../components/Section.jsx'
import { useApp } from '../context/AppContext.jsx'
import { useAsync } from '../hooks/useAsync.js'

export default function AlternativesPage() {
  const { lastScan, member } = useApp()
  const scans = useAsync(() => api.listScans(100), [])
  const [scanId, setScanId] = useState(lastScan?.scan_id ?? null)
  const [state, setState] = useState({ loading: false, data: null, error: null })

  useEffect(() => {
    if (!scanId && scans.data?.length) setScanId(scans.data[0].id)
  }, [scans.data, scanId])

  const load = useCallback(() => {
    if (!scanId) return
    setState({ loading: true, data: null, error: null })
    api
      .alternatives(scanId, member)
      .then((data) => setState({ loading: false, data, error: null }))
      .catch((error) => setState({ loading: false, data: null, error }))
  }, [scanId, member])
  useEffect(load, [load])

  return (
    <div className="space-y-4">
      <Section title="Better alternatives"
        subtitle="Candidates from Open Food Facts + a local Indian products table, filtered by allergens and diet, scored with the same formula. No AI involved.">
        {scans.loading && <Spinner />}
        <ErrorBox error={scans.error} onRetry={scans.run} />
        {scans.data && scans.data.length === 0 && <Empty title="No scans yet">Scan a label first.</Empty>}
        {scans.data?.length > 0 && (
          <ScanPicker id="alt-scan" label="Find alternatives for" scans={scans.data} value={scanId} onChange={setScanId} />
        )}
      </Section>
      {scanId && (
        <Section title={state.data ? `Instead of ${state.data.base.product_name || 'this'} (${state.data.base.score}/100)` : 'Results'}
          subtitle={state.data ? `Safe for: ${state.data.for_members.join(', ')}. Thumbs up/down re-ranks future suggestions.` : null}>
          <AlternativesList result={state.data} loading={state.loading} error={state.error} onRetry={load} />
        </Section>
      )}
    </div>
  )
}
