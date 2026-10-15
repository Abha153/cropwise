import React, { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import Badge from './Badge'
import { useI18n } from '../i18n/I18nContext'
import { formatTimestamp } from '../utils/datetime'

// Offer -> Counteroffer -> Accept / Reject -> Agreement -> Transaction record.
// Backend contract: backend/app/routers/negotiations.py. The server decides
// whose turn it is (`can`), so the buttons here only mirror what it allows.

const ROUND_TONE = { PROPOSED: 'info', COUNTERED: 'neutral', ACCEPTED: 'success', REJECTED: 'warning', WITHDRAWN: 'neutral' }
const PICKUP_MODES = ['BUYER_PICKUP', 'FARMER_DELIVERY', 'TO_BE_AGREED']

function TermsList({ terms }) {
  const { t } = useI18n()
  const rows = [
    ['negotiation.term.price', `₹${terms.price_per_kg}/kg`],
    ['negotiation.term.quantity', `${Number(terms.quantity_kg).toLocaleString()} kg`],
    ['negotiation.term.quality', terms.quality_grade ? `${t('negotiation.grade')} ${terms.quality_grade}` : null],
    ['negotiation.term.qualityNotes', terms.quality_notes],
    ['negotiation.term.pickupMode', terms.pickup_mode ? t(`negotiation.pickup.${terms.pickup_mode}`) : null],
    ['negotiation.term.pickupDate', terms.pickup_date],
    ['negotiation.term.deliveryLocation', terms.delivery_location],
    ['negotiation.term.deliveryDeadline', terms.delivery_deadline],
  ].filter(([, v]) => v)
  return (
    <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
      {rows.map(([k, v]) => (
        <div key={k} className="contents">
          <dt className="text-ink/50 dark:text-paper/50">{t(k)}</dt>
          <dd className="font-medium break-words">{v}</dd>
        </div>
      ))}
    </dl>
  )
}

function RoundCard({ round }) {
  const { t } = useI18n()
  return (
    <li className="bg-white dark:bg-white/5 border border-black/5 dark:border-white/10 rounded-lg p-3">
      <div className="flex items-center justify-between gap-2 mb-2 flex-wrap">
        <span className="text-xs font-semibold">
          {t('negotiation.roundLabel', { n: round.round_no })} · {t(`negotiation.by.${round.proposed_by}`)}
        </span>
        <Badge tone={ROUND_TONE[round.status] || 'neutral'}>{t(`negotiation.roundStatus.${round.status}`)}</Badge>
      </div>
      <TermsList terms={round} />
      {round.message && <p className="text-xs italic text-ink/60 dark:text-paper/60 mt-2">“{round.message}”</p>}
      <p className="text-[11px] text-ink/40 dark:text-paper/40 mt-2">
        {formatTimestamp(round.created_at)}
        {round.responded_at && round.status !== 'PROPOSED' && ` · ${t('negotiation.closedAt', { when: formatTimestamp(round.responded_at) })}`}
      </p>
    </li>
  )
}

export function AgreementCard({ agreement, transactionId }) {
  const { t } = useI18n()
  if (!agreement) return null
  return (
    <div className="bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-900 rounded-lg p-3 space-y-2">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <h4 className="text-sm font-semibold text-emerald-800 dark:text-emerald-300">{t('negotiation.agreedTerms')}</h4>
        <span className="text-[11px] text-ink/50 dark:text-paper/50">
          {t('negotiation.agreedOn', { when: formatTimestamp(agreement.agreed_at), by: t(`negotiation.by.${agreement.accepted_by}`) })}
        </span>
      </div>
      <TermsList terms={agreement.terms} />
      <p className="text-[11px] text-ink/50 dark:text-paper/50 font-mono-data break-all">
        {t('negotiation.recordFingerprint')}: {agreement.terms_hash.slice(0, 16)}… · {t('negotiation.afterRounds', { n: agreement.rounds_count })}
      </p>
      {transactionId && (
        <Link to={`/transactions/${transactionId}`} className="text-xs font-semibold text-forest underline">
          {t('negotiation.viewTransaction', { id: transactionId })}
        </Link>
      )}
    </div>
  )
}

function CounterForm({ current, onSubmit, onCancel, busy }) {
  const { t } = useI18n()
  const last = current.rounds[current.rounds.length - 1]
  const [f, setF] = useState({
    price_per_kg: last.price_per_kg, quantity_kg: last.quantity_kg,
    quality_grade: last.quality_grade || '', quality_notes: last.quality_notes || '',
    pickup_mode: last.pickup_mode || '', pickup_date: last.pickup_date || '',
    delivery_location: last.delivery_location || '', delivery_deadline: last.delivery_deadline || '',
    message: '',
  })
  const set = (k) => (e) => setF(prev => ({ ...prev, [k]: e.target.value }))

  function submit(e) {
    e.preventDefault()
    // Send only what differs from the proposal being answered.
    const body = {}
    for (const k of ['price_per_kg', 'quantity_kg']) if (Number(f[k]) !== Number(last[k])) body[k] = Number(f[k])
    for (const k of ['quality_grade', 'quality_notes', 'pickup_mode', 'pickup_date', 'delivery_location', 'delivery_deadline']) {
      if (f[k] && f[k] !== (last[k] || '')) body[k] = f[k]
    }
    if (f.message.trim()) body.message = f.message.trim()
    onSubmit(body)
  }

  const input = 'w-full bg-white dark:bg-white/5 border border-black/10 dark:border-white/15 rounded-lg px-2 py-1.5 text-xs'
  const label = 'block text-[11px] text-ink/60 dark:text-paper/60 mb-0.5'
  return (
    <form onSubmit={submit} className="bg-white dark:bg-white/5 border border-black/10 dark:border-white/15 rounded-lg p-3 space-y-3">
      <h4 className="text-sm font-semibold">{t('negotiation.counterTitle')}</h4>
      <p className="text-[11px] text-ink/50 dark:text-paper/50">{t('negotiation.counterHint')}</p>
      <div className="grid grid-cols-2 gap-3">
        <div><label className={label}>{t('negotiation.term.price')}</label>
          <input type="number" min="0" step="0.01" className={input} value={f.price_per_kg} onChange={set('price_per_kg')} /></div>
        <div><label className={label}>{t('negotiation.term.quantity')}</label>
          <input type="number" min="0" step="0.01" className={input} value={f.quantity_kg} onChange={set('quantity_kg')} /></div>
        <div><label className={label}>{t('negotiation.term.quality')}</label>
          <select className={input} value={f.quality_grade} onChange={set('quality_grade')}>
            <option value="">{t('negotiation.notSpecified')}</option>
            {['A', 'B', 'C'].map(g => <option key={g} value={g}>{t('negotiation.grade')} {g}</option>)}
          </select></div>
        <div><label className={label}>{t('negotiation.term.pickupMode')}</label>
          <select className={input} value={f.pickup_mode} onChange={set('pickup_mode')}>
            <option value="">{t('negotiation.notSpecified')}</option>
            {PICKUP_MODES.map(m => <option key={m} value={m}>{t(`negotiation.pickup.${m}`)}</option>)}
          </select></div>
        <div><label className={label}>{t('negotiation.term.pickupDate')}</label>
          <input type="date" className={input} value={f.pickup_date} onChange={set('pickup_date')} /></div>
        <div><label className={label}>{t('negotiation.term.deliveryDeadline')}</label>
          <input type="date" className={input} value={f.delivery_deadline} onChange={set('delivery_deadline')} /></div>
      </div>
      <div><label className={label}>{t('negotiation.term.deliveryLocation')}</label>
        <input maxLength={200} className={input} value={f.delivery_location} onChange={set('delivery_location')} /></div>
      <div><label className={label}>{t('negotiation.term.qualityNotes')}</label>
        <textarea maxLength={500} rows={2} className={input} value={f.quality_notes} onChange={set('quality_notes')} /></div>
      <div><label className={label}>{t('negotiation.message')}</label>
        <textarea maxLength={500} rows={2} className={input} value={f.message} onChange={set('message')} /></div>
      <div className="flex gap-2">
        <button disabled={busy} type="submit" className="text-xs bg-forest text-paper rounded-lg px-3 py-1.5 font-semibold disabled:opacity-60">
          {busy ? t('negotiation.working') : t('negotiation.sendCounter')}
        </button>
        <button type="button" onClick={onCancel} className="text-xs border border-black/10 dark:border-white/15 rounded-lg px-3 py-1.5 font-semibold">{t('cancel')}</button>
      </div>
    </form>
  )
}

export default function NegotiationPanel({ offerId, onChanged }) {
  const { t } = useI18n()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [countering, setCountering] = useState(false)

  const load = useCallback(() => {
    api.getNegotiation(offerId).then(setData).catch(e => setError(e.message))
  }, [offerId])
  useEffect(() => { load() }, [load])

  async function run(action) {
    setBusy(true); setError('')
    try {
      const next = await action()
      setData(next)
      setCountering(false)
      if (onChanged) onChanged(next)
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  if (error && !data) return <p className="text-xs text-red-600">{error}</p>
  if (!data) return <p className="text-xs text-ink/50 dark:text-paper/50">{t('common.loading')}</p>

  const closed = data.offer_status !== 'pending'
  return (
    <div className="space-y-3">
      {error && <p className="text-xs text-red-600">{error}</p>}
      <div className="flex items-center gap-2 flex-wrap text-xs">
        <Badge tone={data.offer_status === 'accepted' ? 'success' : closed ? 'neutral' : 'info'}>{t(`offer.status.${data.offer_status}`)}</Badge>
        {data.awaiting && (
          <span className="text-ink/60 dark:text-paper/60">
            {data.awaiting === data.viewer_role ? t('negotiation.yourTurn') : t('negotiation.waitingFor', { who: t(`negotiation.by.${data.awaiting}`) })}
          </span>
        )}
      </div>

      <ol className="space-y-2">{data.rounds.map(r => <RoundCard key={r.id} round={r} />)}</ol>

      <AgreementCard agreement={data.agreement} transactionId={data.transaction_id} />

      {countering ? (
        <CounterForm current={data} busy={busy} onCancel={() => setCountering(false)}
          onSubmit={(body) => run(() => api.counterOffer(offerId, body))} />
      ) : (
        <div className="flex gap-2 flex-wrap">
          {data.can.accept && (
            <button disabled={busy} onClick={() => run(() => api.acceptNegotiation(offerId))}
              className="text-xs bg-forest text-paper rounded-lg px-3 py-1.5 font-semibold disabled:opacity-60">{t('negotiation.accept')}</button>
          )}
          {data.can.counter && (
            <button disabled={busy} onClick={() => setCountering(true)}
              className="text-xs bg-marigold/90 text-ink rounded-lg px-3 py-1.5 font-semibold disabled:opacity-60">{t('negotiation.counter')}</button>
          )}
          {data.can.reject && (
            <button disabled={busy} onClick={() => run(() => api.rejectNegotiation(offerId))}
              className="text-xs border border-red-200 text-red-500 rounded-lg px-3 py-1.5 font-semibold disabled:opacity-60">{t('negotiation.reject')}</button>
          )}
          {data.can.withdraw && (
            <button disabled={busy} onClick={() => run(() => api.withdrawNegotiation(offerId))}
              className="text-xs border border-black/10 dark:border-white/15 rounded-lg px-3 py-1.5 font-semibold disabled:opacity-60">{t('negotiation.withdraw')}</button>
          )}
        </div>
      )}
    </div>
  )
}
