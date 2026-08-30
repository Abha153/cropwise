import React, { useEffect, useState } from 'react'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import Badge from '../components/Badge'
import LoadingSpinner from '../components/LoadingSpinner'

const VERIFICATION_TIER = {
  PLATFORM_VERIFIED: { label: '✓ Platform Verified', tone: 'success', desc: 'Documents reviewed and verified by CropWise platform team.' },
  DOCUMENT_VERIFIED: { label: '📄 Documents Submitted', tone: 'info', desc: 'Documents submitted, under review.' },
  SELF_DECLARED: { label: '🔵 Self Declared', tone: 'neutral', desc: 'Business details self-reported by buyer. Not independently verified.' },
  PENDING: { label: '⏳ Pending', tone: 'neutral', desc: 'No verification submission yet.' },
}
const STATUS_TONE = {
  PENDING: 'neutral', UNDER_REVIEW: 'info', VERIFIED: 'success',
  REJECTED: 'warning', SUSPENDED: 'warning'
}

function fmt(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}

function BuyerVerificationContent() {
  const [verification, setVerification] = useState(undefined) // undefined = loading, null = not found
  const [form, setForm] = useState({
    business_name: '',
    business_registration_number: '',
    gst_number: '',
    license_number: '',
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  useEffect(() => {
    api.myVerification()
      .then(v => { setVerification(v); setForm(f => ({ ...f, business_name: v.business_name || '', gst_number: v.gst_number || '' })) })
      .catch(() => setVerification(null))
  }, [])

  async function submit(e) {
    e.preventDefault()
    setError(''); setSuccess('')
    setSubmitting(true)
    try {
      const payload = {
        business_name: form.business_name || null,
        business_registration_number: form.business_registration_number || null,
        gst_number: form.gst_number || null,
        license_number: form.license_number || null,
        document_urls: [],
      }
      await api.submitVerification(payload)
      setSuccess('Verification submitted. CropWise admin will review your details.')
      const fresh = await api.myVerification()
      setVerification(fresh)
    } catch (e) { setError(e.message) } finally { setSubmitting(false) }
  }

  const inp = 'w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2 text-sm bg-white dark:bg-white/5 dark:text-paper'
  const lbl = 'text-xs font-semibold text-ink/60 dark:text-paper/60 block mb-1'

  if (verification === undefined) return <LoadingSpinner label="Loading verification status…" />

  const tier = VERIFICATION_TIER[verification?.verification_method || 'PENDING']

  return (
    <div className="max-w-xl space-y-6">
      <div className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-5">
        <h2 className="font-display font-semibold text-base mb-3">Verification Status</h2>
        <div className="space-y-2">
          <div className="flex items-center gap-2 flex-wrap">
            {verification ? (
              <>
                <Badge tone={STATUS_TONE[verification.verification_status] || 'neutral'}>
                  {verification.verification_status}
                </Badge>
                <span className="text-sm font-semibold text-ink/70 dark:text-paper/70">{tier.label}</span>
              </>
            ) : (
              <Badge tone="neutral">Not Submitted</Badge>
            )}
          </div>
          <p className="text-xs text-ink/60 dark:text-paper/60">{tier.desc}</p>
          {verification?.verified_at && (
            <div className="text-xs text-ink/50 dark:text-paper/50">Verified on: {fmt(verification.verified_at)}</div>
          )}
          {verification?.rejected_reason && (
            <div className="text-xs text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/30 rounded px-2 py-1">
              Rejection reason: {verification.rejected_reason}
            </div>
          )}
          {verification?.verification_notes && (
            <div className="text-xs text-ink/60 dark:text-paper/60 bg-wheat/40 rounded px-2 py-1">
              {verification.verification_notes}
            </div>
          )}
        </div>

        <div className="mt-4 pt-4 border-t border-black/5 dark:border-white/10 space-y-1 text-xs text-ink/50 dark:text-paper/50">
          <p>⚠️ CropWise platform verification is NOT government verification or legal certification.</p>
          <p>It confirms that the submitted business documents were reviewed by the CropWise team.</p>
        </div>
      </div>

      {(!verification || ['PENDING', 'REJECTED'].includes(verification.verification_status)) && (
        <div className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-5">
          <h2 className="font-display font-semibold text-base mb-4">Submit Verification Details</h2>
          {error && <div className="text-sm text-red-600 mb-3">{error}</div>}
          {success && <div className="text-sm text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/30 rounded px-3 py-2 mb-3">{success}</div>}
          <form onSubmit={submit} className="space-y-3">
            <div>
              <label className={lbl}>Business / Company Name</label>
              <input value={form.business_name} onChange={e => setForm(f => ({ ...f, business_name: e.target.value }))} className={inp} placeholder="Your registered company name" />
            </div>
            <div>
              <label className={lbl}>Business Registration Number (CIN/LLPIN)</label>
              <input value={form.business_registration_number} onChange={e => setForm(f => ({ ...f, business_registration_number: e.target.value }))} className={inp} placeholder="CIN-UXXXXX..." />
            </div>
            <div>
              <label className={lbl}>GST Number</label>
              <input value={form.gst_number} onChange={e => setForm(f => ({ ...f, gst_number: e.target.value }))} className={inp} placeholder="22XXXXX1234A1ZX" />
            </div>
            <div>
              <label className={lbl}>License Number (FSSAI/APEDA/other)</label>
              <input value={form.license_number} onChange={e => setForm(f => ({ ...f, license_number: e.target.value }))} className={inp} placeholder="Optional" />
            </div>
            <p className="text-xs text-ink/50 dark:text-paper/50">Document upload will be available in a future update. Submitted details will be reviewed by the CropWise team.</p>
            <button disabled={submitting} className="bg-marigold hover:bg-amber-400 text-ink font-semibold rounded-lg px-5 py-2 text-sm disabled:opacity-60">
              {submitting ? 'Submitting…' : 'Submit for review'}
            </button>
          </form>
        </div>
      )}
    </div>
  )
}

// ---- Admin view ----
function AdminVerificationPanel() {
  const [verifications, setVerifications] = useState(null)
  const [statusFilter, setStatusFilter] = useState('UNDER_REVIEW')
  const [busy, setBusy] = useState(null)
  const [error, setError] = useState('')
  const [toast, setToast] = useState('')

  async function load() {
    try {
      const data = await api.adminListVerifications(statusFilter)
      setVerifications(data)
    } catch (e) { setError(e.message); setVerifications([]) }
  }

  useEffect(() => { load() }, [statusFilter]) // eslint-disable-line

  async function approve(buyerId) {
    setBusy(buyerId)
    try {
      await api.adminApproveVerification(buyerId, 'Documents reviewed and approved.')
      setToast(`Buyer #${buyerId} verified.`)
      load()
    } catch (e) { setError(e.message) } finally { setBusy(null) }
  }

  async function reject(buyerId) {
    const reason = window.prompt('Enter rejection reason:')
    if (!reason) return
    setBusy(buyerId)
    try {
      await api.adminRejectVerification(buyerId, reason)
      setToast(`Buyer #${buyerId} rejected.`)
      load()
    } catch (e) { setError(e.message) } finally { setBusy(null) }
  }

  return (
    <div className="max-w-3xl space-y-4">
      <h2 className="font-display font-semibold text-lg">Buyer Verification Review</h2>
      {toast && <div className="text-sm text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/30 rounded px-3 py-2">{toast}<button onClick={() => setToast('')} className="ml-2 underline text-xs">Dismiss</button></div>}
      {error && <div className="text-sm text-red-600">{error}</div>}

      <div className="flex gap-2">
        {['UNDER_REVIEW', 'PENDING', 'VERIFIED', 'REJECTED', 'SUSPENDED'].map(s => (
          <button key={s} onClick={() => setStatusFilter(s)}
            className={`text-xs rounded-lg px-3 py-1.5 font-semibold border ${statusFilter === s ? 'bg-forest text-paper border-forest' : 'border-black/10 dark:border-white/15'}`}>
            {s}
          </button>
        ))}
      </div>

      {verifications === null ? <LoadingSpinner label="Loading…" /> : verifications.length === 0 ? (
        <p className="text-sm text-ink/50 dark:text-paper/50">No verifications in {statusFilter} status.</p>
      ) : (
        <div className="space-y-3">
          {verifications.map(v => (
            <div key={v.id} className="bg-white dark:bg-white/5 rounded-xl border border-black/5 dark:border-white/10 p-4">
              <div className="flex items-start justify-between gap-2 flex-wrap">
                <div>
                  <div className="font-semibold">{v.business_name || `Buyer #${v.buyer_id}`}</div>
                  <div className="text-xs text-ink/50 dark:text-paper/50">
                    {v.gst_number && `GST: ${v.gst_number}`}
                    {v.business_registration_number && ` · CIN: ${v.business_registration_number}`}
                  </div>
                  <div className="text-xs text-ink/40 mt-0.5">Submitted: {fmt(v.created_at)}</div>
                </div>
                <Badge tone={STATUS_TONE[v.verification_status] || 'neutral'}>{v.verification_status}</Badge>
              </div>
              {v.verification_status === 'UNDER_REVIEW' && (
                <div className="flex gap-2 mt-3">
                  <button onClick={() => approve(v.buyer_id)} disabled={busy === v.buyer_id}
                    className="text-xs bg-forest text-paper font-semibold rounded-lg px-3 py-1.5 disabled:opacity-60">
                    {busy === v.buyer_id ? '…' : '✓ Approve'}
                  </button>
                  <button onClick={() => reject(v.buyer_id)} disabled={busy === v.buyer_id}
                    className="text-xs border border-red-300 dark:border-red-800 text-red-600 dark:text-red-400 font-semibold rounded-lg px-3 py-1.5 disabled:opacity-60">
                    {busy === v.buyer_id ? '…' : '✗ Reject'}
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function BuyerVerification() {
  const { role } = useAuth()

  return (
    <div>
      <h1 className="font-display text-3xl font-bold mb-1">
        {role === 'admin' ? '🔍 Verification Review' : '🏢 Business Verification'}
      </h1>
      <p className="text-ink/60 dark:text-paper/60 text-sm mb-6">
        {role === 'admin'
          ? 'Review and approve buyer verification submissions.'
          : 'Verify your business to build trust with farmers and access premium features.'}
      </p>
      {role === 'admin' ? <AdminVerificationPanel /> : <BuyerVerificationContent />}
    </div>
  )
}
