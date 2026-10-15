import React, { useEffect, useState } from 'react'
import { api } from '../api/client'
import { useI18n } from '../i18n/I18nContext'
import ReputationProfile, { StatusChip, SummaryLine } from './ReputationProfile'

// One fetch per partner per page load, even when a partner appears in many rows.
const cache = new Map()

/**
 * Compact reputation chip for a buyer or transport agency, with an optional
 * "why" panel. Renders nothing while loading or on error rather than
 * guessing -- a missing badge is never shown as a bad one.
 */
export default function ReputationBadge({ type, id, className = '' }) {
  const { t } = useI18n()
  const [profile, setProfile] = useState(null)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    let live = true
    if (!id) return
    const key = `${type}:${id}`
    if (!cache.has(key)) {
      cache.set(key, (type === 'buyer' ? api.reputationBuyer(id) : api.reputationTransporter(id)).catch(() => { cache.delete(key); return null }))
    }
    cache.get(key).then(p => { if (live && p) setProfile(p) })
    return () => { live = false }
  }, [type, id])

  if (!profile) return null
  return (
    <div className={className}>
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <StatusChip profile={profile} />
        <SummaryLine profile={profile} />
        <button type="button" onClick={() => setOpen(o => !o)} className="text-xs text-forest font-semibold underline">
          {open ? t('reputation.hide') : t('reputation.whyThis')}
        </button>
      </div>
      {open && (
        <div className="mt-2 bg-white dark:bg-white/5 border border-black/5 dark:border-white/10 rounded-lg p-3">
          <ReputationProfile profile={profile} />
        </div>
      )}
    </div>
  )
}
