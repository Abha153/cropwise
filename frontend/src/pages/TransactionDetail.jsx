import React, { useEffect, useState, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import Badge from '../components/Badge'
import LoadingSpinner from '../components/LoadingSpinner'

const STATUS_LABELS = {
  OFFER_CREATED: 'Offer Created',
  OFFER_ACCEPTED: 'Offer Accepted',
  ORDER_CONFIRMED: 'Order Confirmed',
  LOGISTICS_PENDING: 'Logistics Pending',
  LOGISTICS_CONFIRMED: 'Transport Confirmed',
  PICKED_UP: 'Picked Up',
  IN_TRANSIT: 'In Transit',
  DELIVERED: 'Delivered',
  PAYMENT_PENDING: 'Payment Pending',
  PAYMENT_INITIATED: 'Payment Initiated',
  PAYMENT_RECEIVED: 'Payment Received',
  COMPLETED: 'Completed',
}
const STATUS_TONE = {
  OFFER_CREATED: 'neutral', OFFER_ACCEPTED: 'info', ORDER_CONFIRMED: 'info',
  LOGISTICS_PENDING: 'warning', LOGISTICS_CONFIRMED: 'info', PICKED_UP: 'marigold',
  IN_TRANSIT: 'marigold', DELIVERED: 'success', PAYMENT_PENDING: 'warning',
  PAYMENT_INITIATED: 'info', PAYMENT_RECEIVED: 'success', COMPLETED: 'forest',
}
const PAYMENT_STATUS_TONE = {
  PENDING: 'neutral', DUE: 'warning', INITIATED: 'info',
  PAID: 'success', FAILED: 'warning', DISPUTED: 'warning'
}

// Next action a user can take from each status
const FARMER_NEXT = {
  LOGISTICS_CONFIRMED: 'PICKED_UP',
  PICKED_UP: 'IN_TRANSIT',
  PAYMENT_RECEIVED: 'COMPLETED',
}
const BUYER_NEXT = {
  OFFER_ACCEPTED: 'ORDER_CONFIRMED',
  IN_TRANSIT: 'DELIVERED',
  DELIVERED: 'PAYMENT_PENDING',
  PAYMENT_PENDING: 'PAYMENT_INITIATED',
}
const NEXT_LABEL = {
  LOGISTICS_PENDING: 'Request Transport',
  PICKED_UP: 'Mark Picked Up',
  IN_TRANSIT: 'Mark In Transit',
  COMPLETED: 'Mark Completed',
  ORDER_CONFIRMED: 'Confirm Order',
  DELIVERED: 'Confirm Delivery',
  PAYMENT_PENDING: 'Mark Payment Due',
  PAYMENT_INITIATED: 'Initiate Payment',
}

function fmt(isoStr) {
  if (!isoStr) return '—'
  const d = new Date(isoStr)
  return d.toLocaleString('en-IN', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function Timeline({ events, currentStatus }) {
  return (
    <div className="space-y-0">
      {events.map((e, i) => (
        <div key={e.id} className="flex gap-3">
          <div className="flex flex-col items-center">
            <div className={`w-3 h-3 rounded-full mt-1 flex-shrink-0 ${i === events.length - 1 ? 'bg-forest' : 'bg-marigold'}`} />
            {i < events.length - 1 && <div className="w-0.5 bg-black/10 dark:bg-white/10 flex-1 my-1" />}
          </div>
          <div className="pb-4">
            <div className="text-sm font-semibold">{STATUS_LABELS[e.event_type] || e.event_type}</div>
            {e.description && <div className="text-xs text-ink/60 dark:text-paper/60">{e.description}</div>}
            <div className="text-xs text-ink/40 dark:text-paper/40 mt-0.5">{fmt(e.created_at)}</div>
          </div>
        </div>
      ))}
    </div>
  )
}

function PaymentPanel({ txnId, role, txnAmount, onUpdated }) {
  const [payment, setPayment] = useState(undefined)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const load = useCallback(() => {
    api.paymentForTransaction(txnId).then(setPayment).catch(() => setPayment(null))
  }, [txnId])

  useEffect(() => { load() }, [load])

  async function initiate() {
    setBusy(true); setError('')
    try {
      if (!payment) {
        const created = await api.createPayment({
          transaction_id: txnId, amount: txnAmount,
          payment_method: 'UPI',
        })
        await api.initiatePayment(created.id, 'UPI')
      } else {
        await api.initiatePayment(payment.id, 'UPI')
      }
      load(); onUpdated()
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  async function confirmReceived() {
    if (!payment) return
    setBusy(true); setError('')
    try {
      await api.confirmPaymentReceived(payment.id)
      load(); onUpdated()
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  async function completeTransaction() {
    if (!payment) return
    setBusy(true); setError('')
    try {
      await api.completeTransaction(payment.id)
      load(); onUpdated()
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  if (payment === undefined) return <div className="text-xs text-ink/50">Loading payment…</div>

  return (
    <div className="space-y-3">
      {error && <div className="text-xs text-red-600">{error}</div>}
      {payment ? (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold">₹{payment.amount.toLocaleString('en-IN')}</span>
            <Badge tone={PAYMENT_STATUS_TONE[payment.payment_status] || 'neutral'}>{payment.payment_status}</Badge>
          </div>
          {payment.payment_reference && (
            <div className="text-xs text-ink/50 font-mono-data">Ref: {payment.payment_reference}</div>
          )}
          {payment.is_demo && (
            <div className="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/30 rounded px-2 py-1">
              ⚠️ Demo Simulated Payment — not a real financial transaction
            </div>
          )}
          {payment.payment_due_date && (
            <div className="text-xs text-ink/50">Due: {payment.payment_due_date}</div>
          )}
          <div className="text-xs space-y-1">
            {payment.initiated_at && <div>Initiated: {fmt(payment.initiated_at)}</div>}
            {payment.received_at && <div>Received: {fmt(payment.received_at)}</div>}
          </div>
          {/* Buyer: initiate if pending/due */}
          {role === 'buyer' && ['PENDING', 'DUE'].includes(payment.payment_status) && (
            <button onClick={initiate} disabled={busy}
              className="w-full text-sm bg-forest text-paper font-semibold rounded-lg py-2 disabled:opacity-60">
              {busy ? 'Processing…' : '💸 Initiate Payment (Demo)'}
            </button>
          )}
          {/* Farmer: confirm received if initiated */}
          {role === 'farmer' && payment.payment_status === 'INITIATED' && (
            <button onClick={confirmReceived} disabled={busy}
              className="w-full text-sm bg-forest text-paper font-semibold rounded-lg py-2 disabled:opacity-60">
              {busy ? 'Confirming…' : '✓ Confirm Payment Received (Demo)'}
            </button>
          )}
          {/* Farmer: complete transaction after payment received */}
          {role === 'farmer' && payment.payment_status === 'PAID' && (
            <button onClick={completeTransaction} disabled={busy}
              className="w-full text-sm bg-marigold text-ink font-semibold rounded-lg py-2 disabled:opacity-60">
              {busy ? 'Completing…' : 'Mark Transaction Complete'}
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-2">
          <p className="text-sm text-ink/50 dark:text-paper/50">No payment record yet.</p>
          {role === 'buyer' && (
            <button onClick={initiate} disabled={busy}
              className="w-full text-sm bg-forest text-paper font-semibold rounded-lg py-2 disabled:opacity-60">
              {busy ? 'Creating…' : '💸 Initiate Payment (Demo)'}
            </button>
          )}
          {payment === null && (
            <div className="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/30 rounded px-2 py-1">
              ⚠️ Demo Simulated Payment — not a real financial transaction
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function GrievancePanel({ txnId, role }) {
  const [grievances, setGrievances] = useState(null)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ category: 'PAYMENT', description: '', priority: 'MEDIUM' })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const CATEGORIES = ['PAYMENT', 'QUALITY', 'QUANTITY', 'PRICE', 'DELIVERY', 'LOGISTICS', 'OTHER']
  const STATUS_TONE_G = { OPEN: 'warning', UNDER_REVIEW: 'info', WAITING_FOR_EVIDENCE: 'warning', RESOLVED: 'success', REJECTED: 'neutral', CLOSED: 'neutral' }

  useEffect(() => {
    api.myGrievances().then(all => {
      setGrievances(all.filter(g => g.transaction_id === txnId))
    }).catch(() => setGrievances([]))
  }, [txnId])

  async function submit(e) {
    e.preventDefault()
    if (!form.description.trim()) { setError('Please describe the issue.'); return }
    setSubmitting(true); setError('')
    try {
      await api.raiseGrievance({
        transaction_id: txnId,
        category: form.category,
        description: form.description,
        priority: form.priority,
      })
      setSuccess('Grievance raised. Admin will review shortly.')
      setShowForm(false)
      const all = await api.myGrievances()
      setGrievances(all.filter(g => g.transaction_id === txnId))
    } catch (e) { setError(e.message) } finally { setSubmitting(false) }
  }

  return (
    <div className="space-y-3">
      {success && <div className="text-xs text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/30 rounded px-2 py-1">{success}</div>}
      {error && <div className="text-xs text-red-600">{error}</div>}

      {grievances === null ? (
        <div className="text-xs text-ink/50">Loading…</div>
      ) : grievances.length > 0 ? (
        <div className="space-y-2">
          {grievances.map(g => (
            <div key={g.id} className="border border-black/10 dark:border-white/15 rounded-lg px-3 py-2 text-xs">
              <div className="flex items-center justify-between mb-1">
                <span className="font-semibold">{g.category}</span>
                <Badge tone={STATUS_TONE_G[g.status] || 'neutral'}>{g.status}</Badge>
              </div>
              <p className="text-ink/60 dark:text-paper/60">{g.description}</p>
              {g.resolution && (
                <div className="mt-1 text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/30 rounded px-1.5 py-0.5">
                  Resolution: {g.resolution}
                </div>
              )}
              <div className="text-ink/40 mt-1">{fmt(g.created_at)}</div>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-xs text-ink/50 dark:text-paper/50">No grievances for this transaction.</p>
      )}

      {!showForm ? (
        <button onClick={() => setShowForm(true)}
          className="w-full text-sm border border-red-300 dark:border-red-800 text-red-600 dark:text-red-400 font-semibold rounded-lg py-2 hover:bg-red-50 dark:hover:bg-red-950/30">
          ⚠️ Raise Dispute
        </button>
      ) : (
        <form onSubmit={submit} className="space-y-2 border border-red-200 dark:border-red-900 rounded-lg p-3">
          <div className="flex gap-2">
            <select value={form.category} onChange={e => setForm(f => ({ ...f, category: e.target.value }))}
              className="flex-1 border border-black/10 dark:border-white/15 rounded-lg px-2 py-1.5 text-sm bg-white dark:bg-white/5 dark:text-paper">
              {CATEGORIES.map(c => <option key={c}>{c}</option>)}
            </select>
            <select value={form.priority} onChange={e => setForm(f => ({ ...f, priority: e.target.value }))}
              className="border border-black/10 dark:border-white/15 rounded-lg px-2 py-1.5 text-sm bg-white dark:bg-white/5 dark:text-paper">
              <option>LOW</option><option>MEDIUM</option><option>HIGH</option>
            </select>
          </div>
          <textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
            rows={3} required placeholder="Describe the issue clearly…"
            className="w-full border border-black/10 dark:border-white/15 rounded-lg px-2 py-1.5 text-sm bg-white dark:bg-white/5 dark:text-paper resize-none" />
          <div className="flex gap-2">
            <button type="submit" disabled={submitting}
              className="text-xs bg-red-500 text-white font-semibold rounded-lg px-3 py-1.5 disabled:opacity-60">
              {submitting ? 'Submitting…' : 'Submit grievance'}
            </button>
            <button type="button" onClick={() => setShowForm(false)} className="text-xs text-ink/50 hover:underline">Cancel</button>
          </div>
        </form>
      )}
    </div>
  )
}

export default function TransactionDetail() {
  const { id } = useParams()
  const { role } = useAuth()
  const [txn, setTxn] = useState(null)
  const [timeline, setTimeline] = useState(null)
  const [advancing, setAdvancing] = useState(false)
  const [error, setError] = useState('')
  const [toast, setToast] = useState('')

  const load = useCallback(async () => {
    try {
      const [t, tl] = await Promise.all([
        api.getTransaction(Number(id)),
        api.getTransactionTimeline(Number(id)),
      ])
      setTxn(t)
      setTimeline(tl)
    } catch (e) {
      setError(e.message)
    }
  }, [id])

  useEffect(() => { load() }, [load])

  async function advanceStatus(newStatus) {
    setAdvancing(true); setError('')
    try {
      await api.updateTransactionStatus(Number(id), newStatus)
      setToast(`Status updated to ${STATUS_LABELS[newStatus] || newStatus}`)
      load()
    } catch (e) { setError(e.message) } finally { setAdvancing(false) }
  }

  if (error) return (
    <div className="space-y-3">
      <div className="text-red-600">{error}</div>
      <Link to="/transactions" className="text-sm text-forest underline">← Back to transactions</Link>
    </div>
  )
  if (!txn) return <LoadingSpinner label="Loading transaction…" />

  const nextFarmer = FARMER_NEXT[txn.status]
  const nextBuyer = BUYER_NEXT[txn.status]
  const nextAction = role === 'farmer' ? nextFarmer : role === 'buyer' ? nextBuyer : null
  const canRaiseDispute = !['OFFER_CREATED', 'CANCELLED'].includes(txn.status)

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center gap-3 flex-wrap">
        <Link to="/transactions" className="text-sm text-forest hover:underline">← My Transactions</Link>
        <span className="text-ink/30">/</span>
        <span className="text-sm font-mono-data text-ink/60 dark:text-paper/60">TXN #{txn.id}</span>
      </div>

      {toast && (
        <div className="bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 text-emerald-700 dark:text-emerald-300 text-sm rounded-lg px-3 py-2">
          {toast} <button onClick={() => setToast('')} className="ml-2 underline text-xs">Dismiss</button>
        </div>
      )}

      {/* Transaction overview */}
      <div className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-6">
        <div className="flex items-start justify-between mb-4 flex-wrap gap-2">
          <div>
            <h1 className="font-display font-bold text-xl">Transaction #{txn.id}</h1>
            <div className="text-xs text-ink/50 dark:text-paper/50 mt-0.5">{fmt(txn.created_at)}</div>
          </div>
          <Badge tone={STATUS_TONE[txn.status] || 'neutral'}>{STATUS_LABELS[txn.status] || txn.status}</Badge>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
          <div>
            <div className="text-xs text-ink/40 dark:text-paper/40">Total Value</div>
            <div className="font-mono-data font-bold text-lg">₹{txn.total_amount.toLocaleString('en-IN')}</div>
          </div>
          <div>
            <div className="text-xs text-ink/40 dark:text-paper/40">Price</div>
            <div className="font-semibold">₹{txn.final_price_per_kg}/kg</div>
          </div>
          <div>
            <div className="text-xs text-ink/40 dark:text-paper/40">Quantity</div>
            <div className="font-semibold">{txn.quantity_kg.toLocaleString()} kg</div>
          </div>
          <div>
            <div className="text-xs text-ink/40 dark:text-paper/40">Market</div>
            <div className="font-semibold">{txn.market_used || '—'}</div>
          </div>
        </div>

        {role === 'farmer' && txn.status === 'ORDER_CONFIRMED' && (
          <div className="mt-4 pt-4 border-t border-black/5 dark:border-white/10">
            {/* Real action: create an actual transport request linked to this
                transaction (backend then moves it to LOGISTICS_PENDING once
                the request exists), rather than just flipping the status label. */}
            <Link
              to={`/transport?transaction_id=${txn.id}&lot_id=${txn.lot_id || ''}&pickup_location=${encodeURIComponent(txn.market_used || '')}`}
              className="inline-block bg-forest text-paper font-semibold rounded-lg px-5 py-2 text-sm"
            >
              → Request Transport
            </Link>
          </div>
        )}

        {nextAction && (
          <div className="mt-4 pt-4 border-t border-black/5 dark:border-white/10">
            <button
              onClick={() => advanceStatus(nextAction)}
              disabled={advancing}
              className="bg-forest text-paper font-semibold rounded-lg px-5 py-2 text-sm disabled:opacity-60"
            >
              {advancing ? 'Updating…' : `→ ${NEXT_LABEL[nextAction] || nextAction}`}
            </button>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Timeline */}
        <div className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-5">
          <h2 className="font-display font-semibold text-base mb-4">Transaction Timeline</h2>
          {timeline ? (
            timeline.timeline.length > 0
              ? <Timeline events={timeline.timeline} currentStatus={txn.status} />
              : <p className="text-xs text-ink/50">No events yet.</p>
          ) : <div className="text-xs text-ink/50">Loading…</div>}
        </div>

        <div className="space-y-6">
          {/* Payment */}
          <div className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-5">
            <h2 className="font-display font-semibold text-base mb-4">Payment</h2>
            <PaymentPanel txnId={txn.id} role={role} txnAmount={txn.total_amount} onUpdated={load} />
          </div>

          {/* Grievance */}
          {canRaiseDispute && (
            <div className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-5">
              <h2 className="font-display font-semibold text-base mb-4">Disputes</h2>
              <GrievancePanel txnId={txn.id} role={role} />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
