import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import StatCard from '../components/StatCard'
import Badge from '../components/Badge'
import LoadingSpinner from '../components/LoadingSpinner'

const TXN_STATUS_TONE = {
  OFFER_ACCEPTED: 'info', ORDER_CONFIRMED: 'info', IN_TRANSIT: 'marigold',
  DELIVERED: 'success', PAYMENT_PENDING: 'warning', PAYMENT_INITIATED: 'info',
  PAYMENT_RECEIVED: 'success', COMPLETED: 'forest', completed: 'forest',
}
const VERIF_TIER = {
  PLATFORM_VERIFIED: { label: '✓ Platform Verified', tone: 'success' },
  DOCUMENT_VERIFIED: { label: '📄 Docs Submitted', tone: 'info' },
  SELF_DECLARED: { label: '🔵 Self Declared', tone: 'neutral' },
  PENDING: { label: '⏳ Not verified', tone: 'neutral' },
}

export default function BuyerDashboard() {
  const { user } = useAuth()
  const [myOffers, setMyOffers] = useState(null)
  const [demands, setDemands] = useState(null)
  const [transactions, setTransactions] = useState(null)
  const [verification, setVerification] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      api.myOffers(),
      api.myDemands(),
      api.myTransactions(),
      api.myVerification().catch(() => null),
    ])
      .then(([o, d, t, v]) => { setMyOffers(o); setDemands(d); setTransactions(t); setVerification(v) })
      .catch(e => setError(e.message))
  }, [])

  if (error) return <div className="text-red-600">{error}</div>
  if (!myOffers) return <LoadingSpinner label="Loading your dashboard..." />

  const pendingOffers = myOffers.filter(o => o.status === 'pending')
  const activeDemands = (demands || []).filter(d => d.status === 'ACTIVE')
  const pendingTxns = (transactions || []).filter(t => !['COMPLETED', 'completed'].includes(t.status))

  const tier = VERIF_TIER[verification?.verification_method || 'PENDING']

  return (
    <div>
      <div className="mb-6">
        <h1 className="font-display text-3xl font-bold">Welcome, {user?.company_name} 🏢</h1>
        <p className="text-ink/60 dark:text-paper/60 mt-1">Manage your demands, offers, and transactions.</p>
      </div>

      {/* Verification banner */}
      {(!verification || verification.verification_status !== 'VERIFIED') && (
        <div className="mb-4 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-xl px-4 py-3 flex items-center justify-between gap-3 flex-wrap">
          <div className="text-sm">
            <span className="font-semibold">Your business is not yet verified.</span>
            {' '}Verified buyers get priority access and farmer trust.
          </div>
          <Link to="/buyer-verification" className="text-sm bg-amber-400 text-ink font-semibold rounded-lg px-3 py-1.5 hover:bg-amber-300">
            Verify Now →
          </Link>
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard label="Active Demands" value={activeDemands.length} icon="🛒" tone="marigold" />
        <StatCard label="Pending Offers" value={pendingOffers.length} icon="⏳" />
        <StatCard label="Active Transactions" value={pendingTxns.length} icon="💼" />
        <StatCard label="Verification" value={tier.label} icon="🏢" />
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
        <Link to="/buyer-demands" className="bg-forest text-paper rounded-2xl p-4 hover:opacity-90 transition-opacity">
          <div className="text-xl mb-1">🛒</div>
          <div className="font-semibold text-sm">My Demands</div>
          <div className="text-xs text-paper/70 mt-0.5">Post buying requirements</div>
        </Link>
        <Link to="/lots" className="bg-white dark:bg-white/5 border border-black/5 dark:border-white/10 shadow-card rounded-2xl p-4 hover:-translate-y-0.5 transition-transform">
          <div className="text-xl mb-1">📦</div>
          <div className="font-semibold text-sm">Browse Lots</div>
          <div className="text-xs text-ink/50 dark:text-paper/50 mt-0.5">Find available crops</div>
        </Link>
        <Link to="/transactions" className="bg-white dark:bg-white/5 border border-black/5 dark:border-white/10 shadow-card rounded-2xl p-4 hover:-translate-y-0.5 transition-transform">
          <div className="text-xl mb-1">💼</div>
          <div className="font-semibold text-sm">Transactions</div>
          <div className="text-xs text-ink/50 dark:text-paper/50 mt-0.5">Track orders & payments</div>
        </Link>
        <Link to="/buyer-verification" className="bg-white dark:bg-white/5 border border-black/5 dark:border-white/10 shadow-card rounded-2xl p-4 hover:-translate-y-0.5 transition-transform">
          <div className="text-xl mb-1">🏢</div>
          <div className="font-semibold text-sm">Verification</div>
          <div className="text-xs text-ink/50 dark:text-paper/50 mt-0.5">Build buyer trust</div>
        </Link>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Active transactions */}
        <div className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-display font-semibold text-lg">Active Transactions</h2>
            <Link to="/transactions" className="text-sm text-forest font-semibold hover:underline">All →</Link>
          </div>
          {pendingTxns.length === 0 ? (
            <p className="text-sm text-ink/50 dark:text-paper/50">No active transactions.</p>
          ) : (
            <div className="space-y-2">
              {pendingTxns.slice(0, 4).map(t => (
                <Link key={t.id} to={`/transactions/${t.id}`} className="flex items-center justify-between border border-black/5 dark:border-white/10 rounded-xl px-4 py-3 hover:bg-wheat/30 dark:hover:bg-white/5 transition-colors">
                  <div>
                    <div className="font-medium text-sm">Transaction #{t.id}</div>
                    <div className="text-xs text-ink/50 dark:text-paper/50">₹{t.total_amount.toLocaleString('en-IN')} · {t.quantity_kg.toLocaleString()} kg</div>
                  </div>
                  <Badge tone={TXN_STATUS_TONE[t.status] || 'neutral'} className="text-xs">{t.status.replace(/_/g, ' ')}</Badge>
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* My demands */}
        <div className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-display font-semibold text-lg">My Active Demands</h2>
            <Link to="/buyer-demands" className="text-sm text-forest font-semibold hover:underline">All →</Link>
          </div>
          {activeDemands.length === 0 ? (
            <p className="text-sm text-ink/50 dark:text-paper/50">No active demands. <Link to="/buyer-demands" className="text-forest underline">Post one →</Link></p>
          ) : (
            <div className="space-y-2">
              {activeDemands.slice(0, 4).map(d => (
                <div key={d.id} className="border border-black/5 dark:border-white/10 rounded-xl px-4 py-3">
                  <div className="flex items-center justify-between">
                    <div className="font-medium text-sm">{d.crop}</div>
                    <span className="text-xs font-mono-data text-forest">
                      {d.target_price_per_kg ? `₹${(d.target_price_per_kg * 100).toFixed(0)}/q` : 'Open price'}
                    </span>
                  </div>
                  <div className="text-xs text-ink/50 dark:text-paper/50">
                    {d.required_quantity_kg.toLocaleString()} kg{d.quality_grade ? ` · Grade ${d.quality_grade}` : ''}
                    {d.delivery_location ? ` · ${d.delivery_location}` : ''}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Recent offers */}
      <div className="mt-6 bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-6">
        <h2 className="font-display font-semibold text-lg mb-4">Recent Offers</h2>
        {myOffers.length === 0 ? (
          <p className="text-sm text-ink/50 dark:text-paper/50">No offers yet. Browse listings in AgriMarket.</p>
        ) : (
          <div className="space-y-2">
            {myOffers.slice(0, 5).map(o => (
              <div key={o.id} className="flex items-center justify-between text-sm border-b border-black/5 dark:border-white/10 pb-2">
                <span>{o.lot_id ? `Lot #${o.lot_id}` : `Listing #${o.listing_id}`} · ₹{o.offered_price_per_kg}/kg · {o.quantity_kg.toLocaleString()} kg</span>
                <Badge tone={o.status === 'accepted' ? 'success' : o.status === 'rejected' ? 'warning' : 'neutral'}>{o.status}</Badge>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
