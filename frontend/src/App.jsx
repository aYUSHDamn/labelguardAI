import { useState } from 'react'
import { Route, Routes } from 'react-router-dom'
import Disclaimer from './components/Disclaimer.jsx'
import { IconMenu, IconShield } from './components/Icons.jsx'
import Sidebar from './components/Sidebar.jsx'
import { useApp } from './context/AppContext.jsx'
import AboutPage from './pages/AboutPage.jsx'
import AllergyCardsPage from './pages/AllergyCardsPage.jsx'
import DecoderPage from './pages/DecoderPage.jsx'
import InsightsPage from './pages/InsightsPage.jsx'
import ProductsPage from './pages/ProductsPage.jsx'
import ReportPage from './pages/ReportPage.jsx'
import ShoppingPage from './pages/ShoppingPage.jsx'
import AlternativesPage from './pages/AlternativesPage.jsx'
import ComparePage from './pages/ComparePage.jsx'
import ProfilePage from './pages/ProfilePage.jsx'
import ScanPage from './pages/ScanPage.jsx'
import TrackerPage from './pages/TrackerPage.jsx'

function BackendStatus() {
  const { health } = useApp()
  if (!health) return null
  if (health.status === 'down')
    return (
      <p className="mb-5 rounded-xl border border-bad-line bg-bad-bg px-4 py-2.5 text-sm text-bad-ink">
        Can't reach the server. Start the backend with <code className="font-semibold">uvicorn main:app --reload</code> in /backend.
      </p>
    )
  if (!health.llm_configured)
    return (
      <p className="mb-5 rounded-xl border border-warn-line bg-warn-bg px-4 py-2.5 text-sm text-warn-ink">
        No Gemini key on the server: photo scans are off. Demo labels, rules and alternatives still work.
      </p>
    )
  return null
}

export default function App() {
  const [menuOpen, setMenuOpen] = useState(false)
  return (
    <div className="min-h-screen">
      <Sidebar open={menuOpen} onClose={() => setMenuOpen(false)} />

      {/* Phone-only bar with the menu button; desktop uses the fixed sidebar */}
      <div className="no-print sticky top-0 z-20 flex items-center gap-3 border-b border-line bg-card/95 px-4 py-3 backdrop-blur lg:hidden">
        <button className="rounded-lg p-1.5 hover:bg-surface" onClick={() => setMenuOpen(true)} aria-label="Open menu">
          <IconMenu />
        </button>
        <span className="grid h-7 w-7 place-items-center rounded-lg bg-brand text-brand-ink"><IconShield width={16} height={16} /></span>
        <span className="font-extrabold tracking-tight">LabelGuard</span>
      </div>

      <div className="lg:pl-64">
        <div className="mx-auto max-w-5xl px-4 py-6 sm:px-6 lg:py-8">
          <BackendStatus />
          <main>
            <Routes>
              <Route path="/" element={<ScanPage />} />
              <Route path="/alternatives" element={<AlternativesPage />} />
              <Route path="/compare" element={<ComparePage />} />
              <Route path="/tracker" element={<TrackerPage />} />
              <Route path="/profile" element={<ProfilePage />} />
              <Route path="/about" element={<AboutPage />} />
              <Route path="/products" element={<ProductsPage />} />
              <Route path="/decoder" element={<DecoderPage />} />
              <Route path="/insights" element={<InsightsPage />} />
              <Route path="/report" element={<ReportPage />} />
              <Route path="/shopping" element={<ShoppingPage />} />
              <Route path="/allergy-cards" element={<AllergyCardsPage />} />
              <Route path="*" element={<ScanPage />} />
            </Routes>
          </main>
          <footer className="no-print mt-12 border-t border-line pb-8 pt-5">
            <Disclaimer />
          </footer>
        </div>
      </div>
    </div>
  )
}
