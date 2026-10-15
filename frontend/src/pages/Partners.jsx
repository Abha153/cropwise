import React, { useEffect, useState } from 'react'
import { ShieldCheck } from 'lucide-react'
import { api } from '../api/client'
import LoadingSpinner from '../components/LoadingSpinner'
import ReputationProfile, { StatusChip, SummaryLine } from '../components/ReputationProfile'
import VerificationBadge from '../components/VerificationBadge'
import { useI18n } from '../i18n/I18nContext'

const METHOD_KEYS = ['recorded', 'sample', 'insufficient', 'contested', 'simulated', 'noScore']

function PartnerCard({ profile }) {
  const { t } = useI18n()
  const [open, setOpen] = useState(false)
  return (
    <div className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-semibold flex items-center gap-2">
            {profile.ranking.position && <span className="font-mono-data text-xs text-ink/50 dark:text-paper/50">#{profile.ranking.position}</span>}
            {profile.name}
            {profile.partner_type === 'buyer' && <VerificationBadge buyerId={profile.partner_id} compact />}
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-2"><StatusChip profile={profile} /><SummaryLine profile={profile} /></div>
        </div>
        <button onClick={() => setOpen(o => !o)} className="text-xs text-forest font-semibold underline shrink-0">
          {open ? t('reputation.hide') : t('reputation.whyThis')}
        </button>
      </div>
      {open && <div className="mt-3"><ReputationProfile profile={profile} /></div>}
    </div>
  )
}

export default function Partners() {
  const { t } = useI18n()
  const [tab, setTab] = useState('transporters')
  const [data, setData] = useState({})
  const [error, setError] = useState('')
  const [showMethod, setShowMethod] = useState(false)

  useEffect(() => {
    if (data[tab]) return
    const call = tab === 'buyers' ? api.reputationBuyers : api.reputationTransporters
    call().then(rows => setData(d => ({ ...d, [tab]: rows }))).catch(e => setError(e.message))
  }, [tab, data])

  const rows = data[tab]
  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-center gap-2 mb-1">
        <ShieldCheck size={22} className="text-forest" />
        <h1 className="font-display text-3xl font-bold">{t('reputation.title')}</h1>
      </div>
      <p className="text-ink/60 dark:text-paper/60 mb-4">{t('reputation.subtitle')}</p>
      <button onClick={() => setShowMethod(s => !s)} className="text-xs text-forest font-semibold underline mb-3">{t('reputation.howItWorks')}</button>
      {showMethod && (
        <ul className="list-disc pl-5 text-sm text-ink/70 dark:text-paper/70 mb-4 space-y-1">
          {METHOD_KEYS.map(k => <li key={k}>{t(`reputation.method.${k}`)}</li>)}
        </ul>
      )}
      <div className="flex gap-2 mb-4">
        {['transporters', 'buyers'].map(k => (
          <button key={k} onClick={() => { setTab(k); setError('') }}
            className={`px-4 py-1.5 rounded-full text-sm font-semibold border ${tab === k ? 'bg-forest text-paper border-forest' : 'border-black/10 dark:border-white/20'}`}>
            {t(`reputation.tab.${k}`)}
          </button>
        ))}
      </div>
      {error && <p className="text-sm text-red-600 mb-3">{error}</p>}
      {!rows && !error && <LoadingSpinner />}
      {rows && rows.length === 0 && <p className="text-sm text-ink/50 dark:text-paper/50">{t('reputation.none')}</p>}
      <div className="space-y-3">{(rows || []).map(p => <PartnerCard key={`${p.partner_type}-${p.partner_id}`} profile={p} />)}</div>
    </div>
  )
}
