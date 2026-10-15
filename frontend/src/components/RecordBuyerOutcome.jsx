import React, { useState } from 'react'
import { api } from '../api/client'
import { useI18n } from '../i18n/I18nContext'

const METRICS = [
  { metric: 'BUYER_PICKUP', labelKey: 'reputation.record.pickup', results: ['ON_TIME', 'LATE', 'NO_SHOW'] },
  { metric: 'BUYER_TERMS', labelKey: 'reputation.record.terms', results: ['AS_AGREED', 'DEVIATED'] },
]

/**
 * Farmer records what actually happened with the buyer on this transaction.
 * This is the only source of buyer pickup / terms evidence -- nothing is
 * assumed. The buyer can see and contest what is recorded here.
 */
export default function RecordBuyerOutcome({ transactionId }) {
  const { t } = useI18n()
  const [choice, setChoice] = useState({})
  const [done, setDone] = useState({})
  const [busy, setBusy] = useState(null)
  const [error, setError] = useState('')

  async function save(metric) {
    setBusy(metric); setError('')
    try {
      await api.recordBuyerOutcome({ transaction_id: transactionId, metric, result: choice[metric] })
      setDone(d => ({ ...d, [metric]: true }))
    } catch (e) { setError(e.message) } finally { setBusy(null) }
  }

  return (
    <div className="space-y-3">
      <p className="text-xs text-ink/60 dark:text-paper/60">{t('reputation.record.hint')}</p>
      {error && <p className="text-xs text-red-600">{error}</p>}
      {METRICS.map(({ metric, labelKey, results }) => (
        <div key={metric} className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-medium w-32">{t(labelKey)}</span>
          {done[metric] ? (
            <span className="text-xs text-emerald-700 dark:text-emerald-400 font-semibold">{t('reputation.record.saved')}</span>
          ) : (
            <>
              <select value={choice[metric] || ''} onChange={e => setChoice(c => ({ ...c, [metric]: e.target.value }))}
                className="border border-black/10 dark:border-white/20 rounded-lg px-2 py-1 text-sm bg-transparent">
                <option value="">{t('reputation.record.choose')}</option>
                {results.map(r => <option key={r} value={r}>{t(`reputation.result.${r}`)}</option>)}
              </select>
              <button disabled={!choice[metric] || busy === metric} onClick={() => save(metric)}
                className="bg-forest text-paper text-xs font-semibold rounded-lg px-3 py-1.5 disabled:opacity-50">
                {t('reputation.record.save')}
              </button>
            </>
          )}
        </div>
      ))}
    </div>
  )
}
