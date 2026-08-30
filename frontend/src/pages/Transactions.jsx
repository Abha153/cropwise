import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import Badge from '../components/Badge'
import LoadingSpinner from '../components/LoadingSpinner'

const STATUS_TONE = {
  OFFER_CREATED: 'neutral', OFFER_ACCEPTED: 'info', ORDER_CONFIRMED: 'info',
  LOGISTICS_PENDING: 'warning', LOGISTICS_CONFIRMED: 'info', PICKED_UP: 'marigold',
  IN_TRANSIT: 'marigold', DELIVERED: 'success', PAYMENT_PENDING: 'warning',
  PAYMENT_INITIATED: 'info', PAYMENT_RECEIVED: 'success', COMPLETED: 'forest',
  // Legacy
  completed: 'forest',
}
const STATUS_LABEL = {
  OFFER_CREATED: 'Offer Created', OFFER_ACCEPTED: 'Offer Accepted',
  ORDER_CONFIRMED: 'Confirmed', LOGISTICS_PENDING: 'Transport Pending',
  LOGISTICS_CONFIRMED: 'Transport Confirmed', PICKED_UP: 'Picked Up',
  IN_TRANSIT: 'In Transit', DELIVERED: 'Delivered',
  PAYMENT_PENDING: 'Payment Pending', PAYMENT_INITIATED: 'Payment Initiated',
  PAYMENT_RECEIVED: 'Payment Received', COMPLETED: 'Completed',
  completed: 'Completed',
}

function fmt(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}

export default function Transactions() {
  const [txns, setTxns] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.myTransactions()
      .then(setTxns)
      .catch(e => { setError(e.message); setTxns([]) })
  }, [])

  if (error) return <div className="text-red-600 text-sm">{error}</div>
  if (!txns) return <LoadingSpinner label="Loading transactions…" />

  return (
    <div>
      <h1 className="font-display text-3xl font-bold mb-1">💼 My Transactions</h1>
      <p className="text-ink/60 dark:text-paper/60 text-sm mb-6">Track all your orders, deliveries, and payments.</p>

      {txns.length === 0 ? (
        <p className="text-sm text-ink/50 dark:text-paper/50">No transactions yet.</p>
      ) : (
        <div className="space-y-3">
          {txns.map(t => (
            <Link
              key={t.id}
              to={`/transactions/${t.id}`}
              className="block bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 px-5 py-4 hover:-translate-y-0.5 transition-transform"
            >
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div>
                  <div className="font-semibold">Transaction #{t.id}</div>
                  <div className="text-xs text-ink/50 dark:text-paper/50">
                    ₹{t.final_price_per_kg}/kg · {t.quantity_kg.toLocaleString()} kg · {t.market_used}
                  </div>
                  <div className="text-xs text-ink/40 dark:text-paper/40">{fmt(t.created_at)}</div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <div className="font-mono-data font-bold text-forest">₹{t.total_amount.toLocaleString('en-IN')}</div>
                  </div>
                  <Badge tone={STATUS_TONE[t.status] || 'neutral'}>{STATUS_LABEL[t.status] || t.status}</Badge>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
