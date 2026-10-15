import React from 'react'
import { useI18n } from '../i18n/I18nContext'
import { formatDate } from '../utils/datetime'
import Badge from './Badge'

/**
 * Renders one partner's evidence-based profile exactly as the backend
 * computed it (app/services/reputation.py). It never derives, rounds up or
 * fills in a number: an indicator with no evidence says "Not recorded yet",
 * and a partner without enough history is labelled "Insufficient history"
 * in neutral grey -- never as a poor score.
 */
export function StatusChip({ profile }) {
  const { t } = useI18n()
  return profile.sufficient_history
    ? <Badge tone="success">{t('reputation.established')}</Badge>
    : <Badge tone="neutral">{t('reputation.insufficient')}</Badge>
}

export function SummaryLine({ profile }) {
  const { t } = useI18n()
  const last = profile.recency?.last_activity_at
  return (
    <span className="text-xs text-ink/60 dark:text-paper/60">
      {t('reputation.completedCount', { n: profile.completed_outcomes })}
      {' · '}
      {last ? t('reputation.lastActivity', { date: formatDate(last) }) : t('reputation.noActivity')}
    </span>
  )
}

function Indicator({ ind, simulated }) {
  const { t } = useI18n()
  const measured = ind.status === 'measured'
  return (
    <div className="flex items-start justify-between gap-3 py-2 border-b border-black/5 dark:border-white/10 last:border-0" title={ind.detail || ''}>
      <div>
        <div className="text-sm font-medium">{t(`reputation.ind.${ind.key}`)}</div>
        {measured && ind.last_event_at && (
          <div className="text-xs text-ink/50 dark:text-paper/50">{t('reputation.lastEvent', { date: formatDate(ind.last_event_at) })}</div>
        )}
        {ind.excluded_under_review > 0 && (
          <div className="text-xs text-amber-700 dark:text-amber-400">{t('reputation.excluded', { n: ind.excluded_under_review })}</div>
        )}
        {simulated > 0 && ind.key === 'payment_status' && (
          <div className="text-xs text-ink/50 dark:text-paper/50">{t('reputation.simulatedExcluded', { n: simulated })}</div>
        )}
      </div>
      <div className="text-right shrink-0">
        {measured ? (
          <>
            <div className="font-mono-data font-semibold">{Math.round(ind.value * 100)}%</div>
            <div className="text-xs text-ink/50 dark:text-paper/50">{t('reputation.sample', { num: ind.numerator, den: ind.denominator })}</div>
          </>
        ) : (
          <div className="text-xs text-ink/40 dark:text-paper/40">{t('reputation.notRecorded')}</div>
        )}
      </div>
    </div>
  )
}

export default function ReputationProfile({ profile }) {
  const { t } = useI18n()
  const h = profile.trip_history || profile.transaction_history || {}
  const c = profile.complaints_and_disputes
  const fb = profile.farmer_feedback
  const pay = profile.indicators.find(i => i.key === 'payment_status')
  const historyKeys = profile.partner_type === 'transporter'
    ? [['completed', 'reputation.h.completed'], ['cancelled_by_agency', 'reputation.h.cancelledByAgency'],
       ['cancelled_other_or_unrecorded', 'reputation.h.cancelledOther'], ['contested_items_under_review', 'reputation.h.contested']]
    : [['completed', 'reputation.h.completed'], ['cancelled', 'reputation.h.cancelled'], ['in_progress', 'reputation.h.inProgress']]

  return (
    <div className="space-y-3">
      {!profile.sufficient_history && (
        <p className="text-xs text-ink/60 dark:text-paper/60 bg-wheat/40 dark:bg-white/5 rounded-lg px-3 py-2">
          {t('reputation.insufficientDesc', { min: profile.minimum_required, done: profile.completed_outcomes })}
        </p>
      )}
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink/60 dark:text-paper/60">
        {historyKeys.map(([k, key]) => <span key={k}>{t(key)}: <b className="font-mono-data">{h[k] ?? 0}</b></span>)}
        {profile.recency && (
          <span>{t('reputation.recent', { n: profile.recency['events_last_90_days'] ?? 0, days: 90 })}</span>
        )}
      </div>
      <div>{profile.indicators.map(ind => <Indicator key={ind.key} ind={ind} simulated={ind.key === 'payment_status' ? (pay?.simulated_payments_excluded || 0) : 0} />)}</div>
      {c && (
        <div className="text-xs">
          <div className="font-semibold text-sm mb-0.5">{t('reputation.complaints')}</div>
          <div className="text-ink/70 dark:text-paper/70">
            {t('reputation.complaintsLine', { recorded: c.recorded, pending: c.pending_review, resolved: c.resolved, dismissed: c.dismissed })}
          </div>
          <div className="text-ink/50 dark:text-paper/50 mt-0.5">{t('reputation.complaintsNote')}</div>
        </div>
      )}
      {fb && fb.count > 0 && (
        <div className="text-xs text-ink/70 dark:text-paper/70">
          {t('reputation.feedbackLine', { n: fb.count, avg: fb.average_overall })}
        </div>
      )}
      {profile.ranking && (
        <div className="text-xs text-ink/50 dark:text-paper/50">
          {profile.ranking.position ? t('reputation.rank', { n: profile.ranking.position }) : t('reputation.unranked')}
        </div>
      )}
    </div>
  )
}
