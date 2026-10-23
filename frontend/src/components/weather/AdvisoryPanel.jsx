import React from 'react'
import { Sprout, ShieldCheck, AlertTriangle, AlertOctagon, Info, SprayCan, Wheat, Tractor } from 'lucide-react'
import { useI18n } from '../../i18n/I18nContext'
import { formatClock, formatDayShort } from '../../utils/weatherFormat'
import { localizeInsight, localizeAdvisorySummary, localizeEtc, localizeEtcAssumptions, localizeLimitations } from '../../utils/weatherAdvisoryI18n'

const LEVEL_STYLE = {
  low: { cls: 'bg-emerald-50 text-emerald-800 border-emerald-200 dark:bg-emerald-400/10 dark:text-emerald-200 dark:border-emerald-300/30', Icon: ShieldCheck },
  moderate: { cls: 'bg-amber-50 text-amber-900 border-amber-300 dark:bg-amber-400/10 dark:text-amber-200 dark:border-amber-300/30', Icon: AlertTriangle },
  high: { cls: 'bg-red-50 text-red-900 border-red-300 dark:bg-red-400/10 dark:text-red-200 dark:border-red-300/30', Icon: AlertOctagon },
  info: { cls: 'bg-sky-50 text-sky-900 border-sky-200 dark:bg-sky-400/10 dark:text-sky-200 dark:border-sky-300/30', Icon: Info },
}

function LevelBadge({ level }) {
  const { t } = useI18n()
  const s = LEVEL_STYLE[level] || LEVEL_STYLE.info
  // Text + icon, never colour alone.
  return (
    <span className={`inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full border ${s.cls}`}>
      <s.Icon size={12} aria-hidden="true" />{t(`weatherPage.risk.${level}`)}
    </span>
  )
}

function InsightCard({ item, icon: Icon }) {
  const { t, code } = useI18n()
  const localized = localizeInsight(item, code)
  return (
    <article className="border border-black/5 dark:border-white/10 rounded-xl p-3.5 bg-white dark:bg-white/5">
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <h4 className="font-display font-semibold text-sm flex items-center gap-1.5">
          {Icon && <Icon size={15} className="text-forest dark:text-forest-light" aria-hidden="true" />}{localized.title}
        </h4>
        <LevelBadge level={item.level} />
      </div>
      <p className="text-sm text-ink/80 dark:text-paper/80 leading-relaxed">{localized.message}</p>
      <p className="text-xs text-ink/60 dark:text-paper/60 mt-2"><span className="font-semibold">{t('weatherPage.advisory.because')}</span> {localized.trigger}</p>
      <details className="mt-1.5 text-xs text-ink/50 dark:text-paper/50">
        <summary className="cursor-pointer select-none hover:text-ink dark:hover:text-paper focus:outline-none focus-visible:ring-2 focus-visible:ring-marigold rounded">{t('weatherPage.advisory.basis')}</summary>
        <p className="mt-1 leading-snug">{localized.basis}</p>
      </details>
    </article>
  )
}

export function AdvisorySkeleton() {
  return (
    <div className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-5 animate-pulse" aria-hidden="true">
      <div className="h-4 w-40 bg-wheat dark:bg-white/10 rounded mb-4" />
      <div className="h-16 bg-wheat/60 dark:bg-white/5 rounded-xl mb-3" />
      <div className="grid sm:grid-cols-2 gap-3">{Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-28 bg-wheat/60 dark:bg-white/5 rounded-xl" />)}</div>
    </div>
  )
}

const CROP_I18N_KEY = { wheat: 'auth.crop.wheat', paddy: 'auth.crop.paddyRice', maize: 'auth.crop.maize', tomato: 'auth.crop.tomato', potato: 'auth.crop.potato', onion: 'auth.crop.onion', soybean: 'auth.crop.soybean', groundnut: 'auth.crop.groundnut', mustard: 'auth.crop.mustard', chickpea: 'auth.crop.chanaGram', sugarcane: 'auth.crop.sugarcane' }
const STAGE_I18N_KEY = { initial: 'weatherPage.stage.initial', development: 'weatherPage.stage.development', mid: 'weatherPage.stage.mid', late: 'weatherPage.stage.late' }

const selectCls = 'w-full border border-black/10 dark:border-white/15 rounded-lg px-3 py-2.5 text-sm bg-white dark:bg-white/5 dark:text-paper min-h-[44px] focus:outline-none focus:ring-2 focus:ring-forest/40'

/**
 * Rule-based farming advisory (computed server-side by farm_advisory.py).
 * Props: advisory (API object), crop/stage + onCropChange/onStageChange.
 * The API returns rule-based English advice; the client localizes presentation for all 15 supported languages.
 */
export default function AdvisoryPanel({ advisory, crop, stage, onCropChange, onStageChange }) {
  const { t, code } = useI18n()
  if (!advisory) return null

  const insights = advisory.insights || []
  const risks = insights.filter((i) => i.category === 'temperature' || i.category === 'wind' || i.id === 'heavy_rain')
  const water = insights.filter((i) => i.id === 'rain_outlook' || i.id === 'et0')
  const acts = advisory.activities || {}

  return (
    <section aria-labelledby="wx-adv-title" className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-4 sm:p-5">
      <h2 id="wx-adv-title" className="font-display font-semibold text-base flex items-center gap-2 mb-1">
        <Sprout size={18} className="text-forest dark:text-forest-light" aria-hidden="true" />{t('weatherPage.advisory.title')}
      </h2>
      <p className="text-xs text-ink/60 dark:text-paper/60 mb-4">{t('weatherPage.advisory.subtitle')}</p>

      <div className="grid sm:grid-cols-2 gap-3 mb-4">
        <div>
          <label htmlFor="wx-crop" className="block text-xs font-medium text-ink/60 dark:text-paper/60 mb-1">{t('weatherPage.advisory.cropLabel')}</label>
          <select id="wx-crop" value={crop} onChange={(e) => onCropChange(e.target.value)} className={selectCls}>
            <option value="">{t('weatherPage.advisory.noCrop')}</option>
            {(advisory.supported_crops || []).map((c) => <option key={c.key} value={c.label}>{t(CROP_I18N_KEY[c.key] || c.label)}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="wx-stage" className="block text-xs font-medium text-ink/60 dark:text-paper/60 mb-1">{t('weatherPage.advisory.stageLabel')}</label>
          <select id="wx-stage" value={stage} onChange={(e) => onStageChange(e.target.value)} disabled={!crop} className={`${selectCls} disabled:opacity-60`}>
            <option value="">{t('weatherPage.advisory.noStage')}</option>
            {(advisory.growth_stages || []).map((s) => <option key={s.key} value={s.key}>{t(STAGE_I18N_KEY[s.key] || s.label)}</option>)}
          </select>
        </div>
      </div>

      {!advisory.available ? (
        <p className="text-sm text-ink/60 dark:text-paper/60">{t('weatherPage.advisory.unavailable')}</p>
      ) : (
        <>
          <div className="rounded-xl bg-sage/30 dark:bg-white/5 px-4 py-3 mb-5" role="note">
            <div className="text-[11px] font-semibold uppercase tracking-wide text-ink/60 dark:text-paper/60 mb-1">{t('weatherPage.advisory.today')}</div>
            <p className="text-sm leading-relaxed">{localizeAdvisorySummary(code, advisory)}</p>
          </div>

          <h3 className="font-display font-semibold text-sm mb-2">{t('weatherPage.advisory.risks')}</h3>
          <div className="grid sm:grid-cols-2 gap-3 mb-5">
            {risks.map((i) => <InsightCard key={i.id} item={i} />)}
          </div>

          <h3 className="font-display font-semibold text-sm mb-2">{t('weatherPage.advisory.water')}</h3>
          <div className="grid sm:grid-cols-2 gap-3 mb-3">
            {water.map((i) => <InsightCard key={i.id} item={i} />)}
          </div>
          {advisory.etc && (
            <div className="rounded-xl border border-dashed border-forest/40 dark:border-white/25 p-3.5 mb-5 text-sm">
              <div className="font-semibold mb-1">{t('weatherPage.advisory.etcTitle')}</div>
              <p className="leading-relaxed">{localizeEtc(advisory.etc, t(CROP_I18N_KEY[(advisory.supported_crops || []).find((c) => c.label === crop)?.key] || 'weatherPage.advisory.cropLabel'), t(STAGE_I18N_KEY[stage] || 'weatherPage.advisory.noStage'), code)}</p>
              <ul className="list-disc pl-5 mt-2 text-xs text-ink/60 dark:text-paper/60 space-y-0.5">
                {localizeEtcAssumptions(code).map((a) => <li key={a}>{a}</li>)}
              </ul>
            </div>
          )}

          <h3 className="font-display font-semibold text-sm mb-2 mt-5">{t('weatherPage.advisory.activities')}</h3>
          <div className="grid gap-3 mb-5">
            {acts.spraying && (
              <div>
                <InsightCard item={acts.spraying} icon={SprayCan} />
                {acts.spraying.windows && acts.spraying.windows.length > 0 && (
                  <ul className="mt-2 flex flex-wrap gap-2" aria-label={t('weatherPage.advisory.sprayWindows')}>
                    {acts.spraying.windows.map((w) => (
                      <li key={w.start} className="text-xs font-mono-data px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-900 border border-emerald-200 dark:bg-emerald-400/10 dark:text-emerald-200 dark:border-emerald-300/30">{formatDayShort(w.start, code)} {formatClock(w.start, code)} – {formatClock(w.end, code)}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}
            {acts.harvesting && <InsightCard item={acts.harvesting} icon={Wheat} />}
            {acts.sowing && <InsightCard item={acts.sowing} icon={Tractor} />}
          </div>
        </>
      )}

      {advisory.limitations && advisory.limitations.length > 0 && (
        <div className="rounded-xl bg-mist dark:bg-white/5 px-4 py-3 text-xs text-ink/70 dark:text-paper/70">
          <div className="font-semibold mb-1">{t('weatherPage.advisory.limits')}</div>
          <ul className="list-disc pl-4 space-y-1 leading-snug">
            {localizeLimitations(advisory.limitations, code).map((l) => <li key={l}>{l}</li>)}
          </ul>
        </div>
      )}
    </section>
  )
}
