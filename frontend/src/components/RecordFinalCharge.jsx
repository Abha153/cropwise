import React, { useState } from 'react'
import { api } from '../api/client'
import { useI18n } from '../i18n/I18nContext'

/**
 * Shown to the farmer on a delivered trip. The amount is compared with the
 * agreed price to measure quote accuracy; it can be recorded once and the
 * transport agency can contest it.
 */
export default function RecordFinalCharge({ trip, onRecorded }) {
  const { t } = useI18n()
  const [amount, setAmount] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(trip.final_charge ?? null)

  if (!['DELIVERED', 'COMPLETED'].includes(trip.status)) return null
  if (saved !== null) {
    return <p className="text-xs text-ink/60 dark:text-paper/60 mt-2">{t('reputation.finalCharge.recorded', { amount: saved })}</p>
  }
  async function save() {
    setBusy(true); setError('')
    try {
      const r = await api.recordFinalCharge(trip.id, Number(amount))
      setSaved(r.final_charge); onRecorded && onRecorded(r)
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }
  return (
    <div className="mt-3 bg-wheat/40 dark:bg-white/5 rounded-lg p-3">
      <div className="text-sm font-semibold mb-1">{t('reputation.finalCharge.title')}</div>
      <p className="text-xs text-ink/60 dark:text-paper/60 mb-2">{t('reputation.finalCharge.hint')}</p>
      {error && <p className="text-xs text-red-600 mb-1">{error}</p>}
      <div className="flex gap-2">
        <input type="number" min="1" value={amount} onChange={e => setAmount(e.target.value)} placeholder="₹"
          className="border border-black/10 dark:border-white/20 rounded-lg px-2 py-1 text-sm bg-transparent w-32" />
        <button disabled={!(Number(amount) > 0) || busy} onClick={save}
          className="bg-forest text-paper text-xs font-semibold rounded-lg px-3 py-1.5 disabled:opacity-50">{t('reputation.record.save')}</button>
      </div>
    </div>
  )
}
