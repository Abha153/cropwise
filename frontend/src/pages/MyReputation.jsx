import React, { useCallback, useEffect, useState } from 'react'
import { Scale } from 'lucide-react'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import LoadingSpinner from '../components/LoadingSpinner'
import Badge from '../components/Badge'
import ReputationProfile, { StatusChip, SummaryLine } from '../components/ReputationProfile'
import { useI18n } from '../i18n/I18nContext'
import { formatDate, formatTimestamp } from '../utils/datetime'

const TONE = { OPEN: 'warning', UNDER_REVIEW: 'info', UPHELD: 'success', REJECTED: 'neutral' }
const FIELDS = ['status', 'scheduled_pickup', 'agreed_price', 'final_charge', 'cancelled_by', 'promised_delivery_by', 'metric', 'result', 'note']

function EvidenceRow({ item, dispute, onContested }) {
  const { t } = useI18n()
  const [open, setOpen] = useState(false)
  const [reason, setReason] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const title = item.target_type === 'TRANSPORT_REQUEST'
    ? t('reputation.my.trip', { id: item.target_id })
    : t('reputation.my.record', { id: item.transaction_id })

  async function submit() {
    setBusy(true); setError('')
    try {
      await api.raiseReputationDispute({ target_type: item.target_type, target_id: item.target_id, reason })
      setOpen(false); onContested()
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  return (
    <div className="bg-white dark:bg-white/5 rounded-xl border border-black/5 dark:border-white/10 p-3 text-sm">
      <div className="flex items-center justify-between gap-2">
        <span className="font-semibold">{title}</span>
        {dispute
          ? <Badge tone={TONE[dispute.status]}>{t(`reputation.dispute.${dispute.status}`)}</Badge>
          : <button onClick={() => setOpen(o => !o)} className="text-xs text-forest font-semibold underline">{t('reputation.my.contest')}</button>}
      </div>
      <dl className="mt-1 grid grid-cols-2 gap-x-3 text-xs text-ink/70 dark:text-paper/70">
        {FIELDS.filter(f => item[f] !== undefined && item[f] !== null && item[f] !== '').map(f => (
          <React.Fragment key={f}><dt className="text-ink/50 dark:text-paper/50">{t(`reputation.field.${f}`)}</dt><dd>{String(item[f])}</dd></React.Fragment>
        ))}
        {item.picked_up_at && <><dt className="text-ink/50 dark:text-paper/50">{t('reputation.field.picked_up_at')}</dt><dd>{formatTimestamp(item.picked_up_at)}</dd></>}
        {item.delivered_at && <><dt className="text-ink/50 dark:text-paper/50">{t('reputation.field.delivered_at')}</dt><dd>{formatTimestamp(item.delivered_at)}</dd></>}
        {item.recorded_at && <><dt className="text-ink/50 dark:text-paper/50">{t('reputation.field.recorded_at')}</dt><dd>{formatDate(item.recorded_at)}</dd></>}
      </dl>
      {dispute?.admin_note && <p className="text-xs mt-1">{t('reputation.dispute.reviewerNote')}: {dispute.admin_note}</p>}
      {open && (
        <div className="mt-2 space-y-2">
          <textarea rows={3} value={reason} onChange={e => setReason(e.target.value)} placeholder={t('reputation.my.reasonPlaceholder')}
            className="w-full border border-black/10 dark:border-white/20 rounded-lg px-2 py-1 text-sm bg-transparent" />
          {error && <p className="text-xs text-red-600">{error}</p>}
          <button disabled={reason.trim().length < 10 || busy} onClick={submit}
            className="bg-forest text-paper text-xs font-semibold rounded-lg px-3 py-1.5 disabled:opacity-50">{t('reputation.my.submit')}</button>
        </div>
      )}
    </div>
  )
}

/** A buyer's or transport agency's view of its own profile, the evidence behind it, and the right to contest it. */
export default function MyReputation() {
  const { t } = useI18n()
  const { role, user } = useAuth()
  const [profile, setProfile] = useState(null)
  const [evidence, setEvidence] = useState(null)
  const [disputes, setDisputes] = useState([])
  const [error, setError] = useState('')

  const load = useCallback(() => {
    const getProfile = role === 'buyer' ? api.reputationBuyer : api.reputationTransporter
    Promise.all([getProfile(user.id), api.myReputationEvidence(), api.myReputationDisputes()])
      .then(([p, e, d]) => { setProfile(p); setEvidence(e.items); setDisputes(d) })
      .catch(e => setError(e.message))
  }, [role, user])
  useEffect(() => { if (user) load() }, [user, load])

  if (error) return <p className="text-red-600 text-sm">{error}</p>
  if (!profile) return <LoadingSpinner />
  const disputeFor = item => disputes.find(d => d.target_type === item.target_type && d.target_id === item.target_id)

  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-center gap-2 mb-1">
        <Scale size={22} className="text-forest" />
        <h1 className="font-display text-3xl font-bold">{t('reputation.my.title')}</h1>
      </div>
      <p className="text-ink/60 dark:text-paper/60 mb-4">{t('reputation.my.subtitle')}</p>
      <div className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-4 mb-6">
        <div className="flex flex-wrap items-center gap-2 mb-3"><StatusChip profile={profile} /><SummaryLine profile={profile} /></div>
        <ReputationProfile profile={profile} />
      </div>
      <h2 className="font-display font-semibold text-lg mb-2">{t('reputation.my.evidence')}</h2>
      {evidence.length === 0 && <p className="text-sm text-ink/50 dark:text-paper/50">{t('reputation.my.noEvidence')}</p>}
      <div className="space-y-2">{evidence.map(it => <EvidenceRow key={`${it.target_type}-${it.target_id}`} item={it} dispute={disputeFor(it)} onContested={load} />)}</div>
    </div>
  )
}
