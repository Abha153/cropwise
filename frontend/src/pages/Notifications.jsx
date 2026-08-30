import React, { useEffect, useState } from 'react'
import { api } from '../api/client'
import Badge from '../components/Badge'
import LoadingSpinner from '../components/LoadingSpinner'

const ICONS = { price_drop: '🔴', high_demand: '🟢', opportunity: '🟡', harvest_reminder: '🔵' }

export default function Notifications() {
  const [items, setItems] = useState(null)
  const [generating, setGenerating] = useState(false)

  async function load() {
    const data = await api.myNotifications()
    setItems(data)
  }
  useEffect(() => { load() }, [])

  async function markRead(id) {
    await api.markNotificationRead(id)
    load()
  }

  async function generate() {
    setGenerating(true)
    try {
      await api.generateNotification()
      await load()
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-1 flex-wrap gap-2">
        <h1 className="font-display text-3xl font-bold">🔔 Alerts</h1>
        <button onClick={generate} disabled={generating} className="text-sm bg-marigold hover:bg-marigold-dark text-ink dark:text-paper font-semibold rounded-lg px-4 py-2 transition-colors disabled:opacity-60">
          {generating ? 'Generating...' : '+ Generate new alert (demo)'}
        </button>
      </div>
      <p className="text-ink/60 dark:text-paper/60 mb-6">Price drops, high demand, selling opportunities, and harvest reminders.</p>

      {items === null ? <LoadingSpinner label="Loading alerts..." /> : items.length === 0 ? (
        <p className="text-sm text-ink/50 dark:text-paper/50">No alerts yet.</p>
      ) : (
        <div className="space-y-3">
          {items.map(n => (
            <div key={n.id} className={`bg-white dark:bg-white/5 rounded-xl border border-black/5 dark:border-white/10 shadow-card p-4 flex items-start gap-3 ${n.is_read ? 'opacity-60' : ''}`}>
              <div className="text-2xl">{ICONS[n.type] || 'ℹ️'}</div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold">{n.title}</h3>
                  {!n.is_read && <Badge tone="marigold">New</Badge>}
                </div>
                <p className="text-sm text-ink/60 dark:text-paper/60 mt-0.5">{n.message}</p>
              </div>
              {!n.is_read && (
                <button onClick={() => markRead(n.id)} className="text-xs text-forest font-semibold hover:underline whitespace-nowrap">Mark read</button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
