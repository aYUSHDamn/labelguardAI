import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client.js'
import { Empty, ErrorBox, Spinner } from '../components/Feedback.jsx'
import { IconShare, IconTrash } from '../components/Icons.jsx'
import Section from '../components/Section.jsx'
import { useAsync } from '../hooks/useAsync.js'

export default function ShoppingPage() {
  const list = useAsync(() => api.shopping(), [])
  const [name, setName] = useState('')

  const add = async (e) => {
    e.preventDefault()
    if (!name.trim()) return
    await api.shoppingAdd({ product_name: name.trim() })
    setName('')
    list.run()
  }
  const toggle = async (item) => {
    await api.shoppingToggle(item.id, !item.done)
    list.run()
  }
  const remove = async (item) => {
    await api.shoppingDelete(item.id)
    list.run()
  }
  const items = list.data || []
  const todo = items.filter((i) => !i.done)
  const shareText = 'Shopping list (LabelGuard picks):\n' + todo.map((i) => `☐ ${i.brand ? `${i.brand} ` : ''}${i.product_name}`).join('\n')

  return (
    <div className="space-y-6">
      <Section title="Shopping list" subtitle="Healthier picks saved from scans, alternatives and the product explorer"
        right={todo.length > 0 && (
          <a className="btn-ghost px-3 py-1.5 text-xs" target="_blank" rel="noreferrer" href={`https://wa.me/?text=${encodeURIComponent(shareText)}`}>
            <IconShare width={14} height={14} /> Send on WhatsApp
          </a>
        )}>
        <form onSubmit={add} className="mb-4 flex gap-2">
          <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Add an item, e.g. Rolled oats" />
          <button className="btn-primary shrink-0" disabled={!name.trim()}>Add</button>
        </form>
        {list.loading && !list.data && <Spinner />}
        <ErrorBox error={list.error} onRetry={list.run} />
        {list.data && items.length === 0 && (
          <Empty title="Your list is empty">
            Use "Add to list" on <Link className="text-brand hover:underline" to="/alternatives">alternatives</Link> or in the{' '}
            <Link className="text-brand hover:underline" to="/products">product explorer</Link>.
          </Empty>
        )}
        <ul className="divide-y divide-line">
          {items.map((i) => (
            <li key={i.id} className="flex items-center gap-3 py-3">
              <input type="checkbox" className="h-5 w-5 shrink-0 accent-[rgb(var(--brand))]" checked={!!i.done} onChange={() => toggle(i)}
                aria-label={`Mark ${i.product_name} as bought`} />
              <div className={`min-w-0 flex-1 ${i.done ? 'text-muted line-through' : ''}`}>
                <p className="font-medium">{i.product_name}</p>
                <p className="text-xs text-muted">{[i.brand, i.score != null ? `score ${i.score}/100` : null].filter(Boolean).join(' · ')}</p>
                {i.note && !i.done && <p className="text-xs text-good-ink">{i.note}</p>}
              </div>
              <button className="rounded-lg p-2 text-muted hover:bg-surface hover:text-bad-ink" onClick={() => remove(i)} aria-label={`Remove ${i.product_name}`}>
                <IconTrash width={16} height={16} />
              </button>
            </li>
          ))}
        </ul>
      </Section>
    </div>
  )
}
