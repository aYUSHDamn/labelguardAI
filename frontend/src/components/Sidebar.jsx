import { NavLink } from 'react-router-dom'
import HeaderControls from './HeaderControls.jsx'
import {
  IconBox, IconCamera, IconCard, IconCart, IconChart, IconClose, IconColumns, IconInfo, IconPrint, IconSearch, IconShield,
  IconSpark, IconSwap, IconUsers,
} from './Icons.jsx'

const GROUPS = [
  ['Check food', [
    ['/', 'Scan label', IconCamera],
    ['/alternatives', 'Alternatives', IconSwap],
    ['/compare', 'Compare', IconColumns],
  ]],
  ['Discover', [
    ['/products', 'Product explorer', IconBox],
    ['/decoder', 'Ingredient decoder', IconSearch],
  ]],
  ['My family', [
    ['/tracker', 'Tracker & history', IconChart],
    ['/report', 'Weekly report', IconPrint],
    ['/insights', 'Insights', IconSpark],
    ['/shopping', 'Shopping list', IconCart],
    ['/allergy-cards', 'Allergy cards', IconCard],
    ['/profile', 'Family profile', IconUsers],
  ]],
  ['Project', [
    ['/about', 'About & evaluation', IconInfo],
  ]],
]

// Left sidebar with every module. Fixed on desktop; a slide-out drawer on phones.
export default function Sidebar({ open, onClose }) {
  return (
    <>
      {open && <div className="fixed inset-0 z-30 bg-ink/30 lg:hidden" onClick={onClose} aria-hidden />}
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-line bg-card transition-transform lg:translate-x-0 ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex items-center justify-between px-5 pb-3 pt-5">
          <div className="flex items-center gap-2.5">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-brand text-brand-ink shadow-sm">
              <IconShield width={20} height={20} />
            </span>
            <span className="leading-tight">
              <span className="block text-[17px] font-extrabold tracking-tight">LabelGuard</span>
              <span className="block text-[11px] text-muted">Food labels, decoded</span>
            </span>
          </div>
          <button className="rounded-lg p-1.5 text-muted hover:bg-surface lg:hidden" onClick={onClose} aria-label="Close menu">
            <IconClose />
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto px-3 pb-3" aria-label="Main">
          {GROUPS.map(([title, links]) => (
            <div key={title} className="mt-3">
              <p className="px-3 pb-1.5 text-[11px] font-semibold uppercase tracking-wider text-muted">{title}</p>
              <ul className="space-y-0.5">
                {links.map(([to, label, Icon]) => (
                  <li key={to}>
                    <NavLink
                      to={to}
                      end={to === '/'}
                      onClick={onClose}
                      className={({ isActive }) =>
                        `flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition ${
                          isActive ? 'bg-brand-soft text-brand' : 'text-muted hover:bg-surface hover:text-ink'
                        }`
                      }
                    >
                      <Icon width={18} height={18} />
                      {label}
                    </NavLink>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>

        <div className="border-t border-line p-4">
          <HeaderControls />
        </div>
      </aside>
    </>
  )
}
