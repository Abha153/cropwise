import React, { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import { useI18n } from '../i18n/I18nContext'
import { formatTimestamp } from '../utils/datetime'
import Badge from './Badge'

const TONE = { OPEN: 'warning', UNDER_REVIEW: 'info', UPHELD: 'success', REJECTED: 'neutral' }

/** Admin queue for partners contesting reputation evidence. A written reason is required to decide. */
export default function ReputationDisputesAdmin({ token }) {
  const { t } = useI18n()
  const [rows, setRows] = useState(null)
  const [filter, setFilter] = useState('')
  const [notes, setNotes] = useState({})
  const [error, setError] = useState('')

  const load = useCallback(() => {
    api.adminReputationDisputes(token, filter || undefined).then(setRows).catch(e => setError(e.message))
  }, [token, filter])
  useEffect(() => { load() }, [load])

  async function decide(id, status) {
    setError('')
    try { await api.adminDecideReputationDispute(token, id, { status, admin_note: notes[id] || '' }); load() }
    catch (e) { setError(e.message) }
  }

  return (
    <div className="mt-10">
      <div className="flex items-center justify-between mb-2">
        <h2 className="font-display text-2xl font-bold">{t('reputation.admin.title')}</h2>
        <select value={filter} onChange={e => setFilter(e.target.value)} className="border border-black/10 dark:border-white/20 rounded-lg px-2 py-1 text-sm bg-transparent">
          <option value="">{t('reputation.admin.all')}</option>
          {Object.keys(TONE).map(s => <option key={s} value={s}>{t(`reputation.dispute.${s}`)}</option>)}
        </select>
      </div>
      <p className="text-sm text-ink/60 dark:text-paper/60 mb-4">{t('reputation.admin.desc')}</p>
      {error && <p className="text-sm text-red-600 mb-2">{error}</p>}
      {rows && rows.length === 0 && <p className="text-sm text-ink/40 dark:text-paper/40">{t('reputation.admin.empty')}</p>}
      <div className="space-y-3">
        {(rows || []).map(d => (
          <div key={d.id} className="bg-white dark:bg-white/5 rounded-xl border border-black/5 dark:border-white/10 p-4 text-sm">
            <div className="flex items-center justify-between gap-2">
              <span className="font-semibold">{t(`reputation.role.${d.subject_role}`)} #{d.subject_id} · {d.target_type} #{d.target_id}</span>
              <Badge tone={TONE[d.status]}>{t(`reputation.dispute.${d.status}`)}</Badge>
            </div>
            <p className="mt-1">{d.reason}</p>
            {(d.evidence_urls || []).map(u => <a key={u} href={u} target="_blank" rel="noreferrer" className="block text-xs text-forest underline truncate">{u}</a>)}
            <div className="text-xs text-ink/50 dark:text-paper/50 mt-1">{formatTimestamp(d.created_at)}</div>
            {d.admin_note && <p className="text-xs mt-1">{t('reputation.dispute.reviewerNote')}: {d.admin_note}</p>}
            {['OPEN', 'UNDER_REVIEW'].includes(d.status) && (
              <div className="mt-3 space-y-2">
                <textarea rows={2} value={notes[d.id] || ''} onChange={e => setNotes(n => ({ ...n, [d.id]: e.target.value }))}
                  placeholder={t('reputation.admin.notePlaceholder')} className="w-full border border-black/10 dark:border-white/20 rounded-lg px-2 py-1 text-sm bg-transparent" />
                <div className="flex flex-wrap gap-2">
                  {d.status === 'OPEN' && <button onClick={() => decide(d.id, 'UNDER_REVIEW')} className="text-xs font-semibold border border-black/10 dark:border-white/20 rounded-lg px-3 py-1.5">{t('reputation.admin.underReview')}</button>}
                  <button onClick={() => decide(d.id, 'UPHELD')} className="text-xs font-semibold bg-forest text-paper rounded-lg px-3 py-1.5">{t('reputation.admin.uphold')}</button>
                  <button onClick={() => decide(d.id, 'REJECTED')} className="text-xs font-semibold border border-black/10 dark:border-white/20 rounded-lg px-3 py-1.5">{t('reputation.admin.reject')}</button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
