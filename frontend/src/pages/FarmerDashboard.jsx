import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import StatCard from '../components/StatCard'
import Badge from '../components/Badge'
import LoadingSpinner from '../components/LoadingSpinner'

const TXN_STATUS_TONE = {
  OFFER_ACCEPTED: 'info', ORDER_CONFIRMED: 'info', LOGISTICS_PENDING: 'warning',
  IN_TRANSIT: 'marigold', DELIVERED: 'success', PAYMENT_PENDING: 'warning',
  PAYMENT_INITIATED: 'info', PAYMENT_RECEIVED: 'success', COMPLETED: 'forest', completed: 'forest',
}

export default function FarmerDashboard() {
  const { user } = useAuth()
  const [listings, setListings] = useState(null)
  const [lots, setLots] = useState(null)
  const [transactions, setTransactions] = useState(null)
  const [notifications, setNotifications] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      api.myListings(),
      api.myLots(),
      api.myTransactions(),
      api.myNotifications(),
    ])
      .then(([l, lo, t, n]) => { setListings(l); setLots(lo); setTransactions(t); setNotifications(n) })
      .catch(e => setError(e.message))
  }, [])

  if (error) return <div className="text-red-600">{error}</div>
  if (!listings) return <LoadingSpinner label="Loading your dashboard..." />

  const active = listings.filter(l => l.status === 'active')
  const activeLots = (lots || []).filter(l => l.status === 'AVAILABLE')
  const pendingTxns = (transactions || []).filter(t =>
    !['COMPLETED', 'completed', 'CANCELLED'].includes(t.status)
  )
  const unread = (notifications || []).filter(n => !n.is_read).length

  return (
    <div>
      <div className="mb-6">
        <h1 className="font-display text-3xl font-bold">Namaste, {user?.name?.split(' ')[0]} 👋</h1>
        <p className="text-ink/60 dark:text-paper/60 mt-1">Here's what's happening with your farm business.</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard label="Active Listings" value={active.length} icon="🌾" tone="marigold" />
        <StatCard label="Active Lots" value={activeLots.length} icon="📦" />
        <StatCard label="Active Transactions" value={pendingTxns.length} icon="💼" />
        <StatCard label="Unread Alerts" value={unread} icon="🔔" />
      </div>

      {/* Quick action cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
        <Link to="/lots" className="bg-forest text-paper rounded-2xl p-4 hover:opacity-90 transition-opacity">
          <div className="text-xl mb-1">📦</div>
          <div className="font-semibold text-sm">My Lots</div>
          <div className="text-xs text-paper/70 mt-0.5">Create & manage lots</div>
        </Link>
        <Link to="/buyer-demands" className="bg-white dark:bg-white/5 border border-black/5 dark:border-white/10 shadow-card rounded-2xl p-4 hover:-translate-y-0.5 transition-transform">
          <div className="text-xl mb-1">🛒</div>
          <div className="font-semibold text-sm">Buyer Demands</div>
          <div className="text-xs text-ink/50 dark:text-paper/50 mt-0.5">Browse & respond</div>
        </Link>
        <Link to="/transactions" className="bg-white dark:bg-white/5 border border-black/5 dark:border-white/10 shadow-card rounded-2xl p-4 hover:-translate-y-0.5 transition-transform">
          <div className="text-xl mb-1">💼</div>
          <div className="font-semibold text-sm">Transactions</div>
          <div className="text-xs text-ink/50 dark:text-paper/50 mt-0.5">Track orders & payments</div>
        </Link>
        <Link to="/advisor" className="bg-white dark:bg-white/5 border border-black/5 dark:border-white/10 shadow-card rounded-2xl p-4 hover:-translate-y-0.5 transition-transform">
          <div className="text-xl mb-1">🤖</div>
          <div className="font-semibold text-sm">AgriAdvisor</div>
          <div className="text-xs text-ink/50 dark:text-paper/50 mt-0.5">Best time to sell</div>
        </Link>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Active transactions */}
        <div className="lg:col-span-2 bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-display font-semibold text-lg">Active Transactions</h2>
            <Link to="/transactions" className="text-sm text-forest font-semibold hover:underline">View all →</Link>
          </div>
          {pendingTxns.length === 0 ? (
            <p className="text-sm text-ink/50 dark:text-paper/50">No active transactions. Post a listing or lot to get started.</p>
          ) : (
            <div className="space-y-2">
              {pendingTxns.slice(0, 4).map(t => (
                <Link key={t.id} to={`/transactions/${t.id}`} className="flex items-center justify-between border border-black/5 dark:border-white/10 rounded-xl px-4 py-3 hover:bg-wheat/30 dark:hover:bg-white/5 transition-colors">
                  <div>
                    <div className="font-medium text-sm">Transaction #{t.id}</div>
                    <div className="text-xs text-ink/50 dark:text-paper/50">₹{t.final_price_per_kg}/kg · {t.quantity_kg.toLocaleString()} kg · ₹{t.total_amount.toLocaleString('en-IN')}</div>
                  </div>
                  <Badge tone={TXN_STATUS_TONE[t.status] || 'neutral'} className="text-xs">{t.status.replace(/_/g, ' ')}</Badge>
                </Link>
              ))}
            </div>
          )}
        </div>

        <div className="space-y-4">
          {/* Alerts */}
          <div className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-5">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-display font-semibold">Recent Alerts</h2>
              <Link to="/notifications" className="text-sm text-forest font-semibold hover:underline">All →</Link>
            </div>
            {(notifications || []).length === 0 ? (
              <p className="text-sm text-ink/50 dark:text-paper/50">No alerts yet.</p>
            ) : (
              <div className="space-y-2">
                {notifications.slice(0, 3).map(n => (
                  <div key={n.id} className="text-sm border-l-2 border-marigold pl-3">
                    <div className="font-medium text-xs">{n.title}</div>
                    <div className="text-ink/50 dark:text-paper/50 text-xs">{n.message}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* My lots preview */}
          <div className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-5">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-display font-semibold">My Lots</h2>
              <Link to="/lots" className="text-sm text-forest font-semibold hover:underline">All →</Link>
            </div>
            {activeLots.length === 0 ? (
              <p className="text-sm text-ink/50 dark:text-paper/50">No active lots. <Link to="/lots" className="text-forest underline">Create one →</Link></p>
            ) : (
              <div className="space-y-2">
                {activeLots.slice(0, 3).map(l => (
                  <div key={l.id} className="text-xs border border-black/5 dark:border-white/10 rounded-lg px-3 py-2">
                    <div className="font-semibold">{l.lot_number}</div>
                    <div className="text-ink/50 dark:text-paper/50">{l.crop} · {l.quantity_kg.toLocaleString()} kg · Grade {l.grade}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
        <Link to="/market-intelligence" className="bg-white dark:bg-white/5 border border-black/5 dark:border-white/10 shadow-card rounded-2xl p-4 hover:-translate-y-0.5 transition-transform">
          <div className="text-xl mb-1">📊</div>
          <div className="font-semibold text-sm">Market Prices</div>
          <div className="text-xs text-ink/50 dark:text-paper/50 mt-0.5">Compare mandis</div>
        </Link>
        <Link to="/farmpool" className="bg-white dark:bg-white/5 border border-black/5 dark:border-white/10 shadow-card rounded-2xl p-4 hover:-translate-y-0.5 transition-transform">
          <div className="text-xl mb-1">🚚</div>
          <div className="font-semibold text-sm">FarmPool</div>
          <div className="text-xs text-ink/50 dark:text-paper/50 mt-0.5">Share transport</div>
        </Link>
        <Link to="/group-selling" className="bg-white dark:bg-white/5 border border-black/5 dark:border-white/10 shadow-card rounded-2xl p-4 hover:-translate-y-0.5 transition-transform">
          <div className="text-xl mb-1">🤝</div>
          <div className="font-semibold text-sm">Group Selling</div>
          <div className="text-xs text-ink/50 dark:text-paper/50 mt-0.5">Sell with FPO</div>
        </Link>
        <Link to="/profit-calculator" className="bg-white dark:bg-white/5 border border-black/5 dark:border-white/10 shadow-card rounded-2xl p-4 hover:-translate-y-0.5 transition-transform">
          <div className="text-xl mb-1">🧮</div>
          <div className="font-semibold text-sm">Profit Calculator</div>
          <div className="text-xs text-ink/50 dark:text-paper/50 mt-0.5">Compare options</div>
        </Link>
      </div>
    </div>
  )
}
