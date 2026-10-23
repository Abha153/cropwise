import React from 'react'
import { Droplets, Wind, CloudRain, Gauge, Cloud, Thermometer, Navigation, RefreshCw, Clock } from 'lucide-react'
import { useI18n } from '../../i18n/I18nContext'
import { iconForWeatherCode, weatherConditionKey } from '../../utils/weatherCodes'
import { formatUpdatedAt, ageParts, compassDirection, roundOrDash } from '../../utils/weatherFormat'

function Metric({ Icon, label, value, sub }) {
  return (
    <div className="flex items-start gap-2 bg-mist dark:bg-white/5 rounded-xl px-3 py-2.5">
      <Icon size={16} className="text-forest dark:text-forest-light mt-0.5 shrink-0" aria-hidden="true" />
      <div className="min-w-0">
        <div className="text-[11px] text-ink/60 dark:text-paper/60">{label}</div>
        <div className="font-mono-data text-sm font-semibold">{value}</div>
        {sub && <div className="text-[11px] text-ink/50 dark:text-paper/50">{sub}</div>}
      </div>
    </div>
  )
}

export function WeatherOverviewSkeleton() {
  return (
    <div className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-5 animate-pulse" aria-hidden="true">
      <div className="h-4 w-32 bg-wheat dark:bg-white/10 rounded mb-4" />
      <div className="flex items-center gap-4 mb-4">
        <div className="h-14 w-14 rounded-full bg-wheat dark:bg-white/10" />
        <div className="space-y-2"><div className="h-8 w-24 bg-wheat dark:bg-white/10 rounded" /><div className="h-3 w-32 bg-wheat/70 dark:bg-white/10 rounded" /></div>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
        {Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-14 bg-wheat/60 dark:bg-white/5 rounded-xl" />)}
      </div>
    </div>
  )
}

/**
 * Current conditions. These come from the weather MODEL for the grid cell
 * (not a station at the user's exact spot) and the card says so.
 * `weather` is the API response; `onRefresh` re-fetches.
 */
export default function WeatherOverview({ weather, onRefresh, refreshing }) {
  const { t, code } = useI18n()
  const cur = weather.current
  const Icon = iconForWeatherCode(cur.weather_code, cur.is_day)
  const today = (weather.forecast || [])[0]
  const dir = compassDirection(cur.wind_direction_deg)
  const updated = formatUpdatedAt(weather.fetched_at, weather.utc_offset_seconds, code)
  const age = ageParts(weather.cache && weather.cache.age_seconds)
  const ageText = age ? t(`weatherPage.age.${age.unit}`, { n: age.value }) : null
  const isLive = weather.status === 'LIVE'

  return (
    <section aria-labelledby="wx-now-title" className="bg-white dark:bg-white/5 rounded-2xl shadow-card border border-black/5 dark:border-white/10 p-4 sm:p-5">
      <div className="flex items-start justify-between gap-2 flex-wrap mb-3">
        <h2 id="wx-now-title" className="font-display font-semibold text-base">{t('weatherPage.now.title')}</h2>
        <div className="flex items-center gap-2 text-[11px] text-ink/60 dark:text-paper/60">
          <Clock size={12} aria-hidden="true" />
          {updated ? (
            <span>
              {t('weatherPage.updated', { time: updated })}
              {weather.cache && weather.cache.state === 'fresh' && ` · ${t('weatherPage.cache.fresh', { age: ageText })}`}
              {weather.cache && weather.cache.state === 'stale' && ` · ${t('weatherPage.cache.stale', { age: ageText })}`}
            </span>
          ) : <span>{t('weatherPage.noTimestamp')}</span>}
          <button
            type="button" onClick={onRefresh} disabled={refreshing}
            aria-label={t('common.refresh')} title={t('common.refresh')}
            className="p-1.5 rounded-md hover:bg-mist dark:hover:bg-white/10 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-marigold"
          >
            <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} aria-hidden="true" />
          </button>
        </div>
      </div>

      <div className="flex items-center gap-4 mb-4">
        <Icon size={52} className="text-forest dark:text-forest-light shrink-0" aria-hidden="true" />
        <div>
          <div className="font-mono-data text-4xl font-bold leading-none">{roundOrDash(cur.temperature, 1)}°C</div>
          <div className="text-sm text-ink/70 dark:text-paper/70 mt-1">{t(weatherConditionKey(cur.weather_code))}</div>
          {cur.apparent_temperature != null && (
            <div className="text-xs text-ink/60 dark:text-paper/60">{t('weatherPage.now.feelsLike', { temp: roundOrDash(cur.apparent_temperature, 1) })}</div>
          )}
        </div>
        {cur.is_day != null && (
          <span className="ml-auto text-[11px] font-semibold px-2 py-0.5 rounded-full border border-black/10 dark:border-white/15 text-ink/60 dark:text-paper/60">
            {cur.is_day ? t('weatherPage.now.day') : t('weatherPage.now.night')}
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
        {cur.humidity != null && <Metric Icon={Droplets} label={t('weatherPage.now.humidity')} value={`${roundOrDash(cur.humidity)}%`} />}
        <Metric Icon={Wind} label={t('weatherPage.now.wind')} value={`${roundOrDash(cur.wind_speed_kmh)} km/h${dir ? ` ${dir}` : ''}`}
          sub={cur.wind_gusts_kmh != null ? t('weatherPage.now.gusts', { speed: roundOrDash(cur.wind_gusts_kmh) }) : null} />
        <Metric Icon={CloudRain} label={t('weatherPage.now.rainNow')} value={`${roundOrDash(cur.precipitation_mm, 1)} mm`} />
        {today && today.rainfall_probability != null && (
          <Metric Icon={Navigation} label={t('weatherPage.now.rainChanceToday')} value={`${roundOrDash(today.rainfall_probability)}%`}
            sub={today.rainfall_mm != null ? t('weatherPage.now.rainToday', { mm: roundOrDash(today.rainfall_mm, 1) }) : null} />
        )}
        {cur.cloud_cover_pct != null && <Metric Icon={Cloud} label={t('weatherPage.now.cloud')} value={`${roundOrDash(cur.cloud_cover_pct)}%`} />}
        {cur.pressure_hpa != null && <Metric Icon={Gauge} label={t('weatherPage.now.pressure')} value={`${roundOrDash(cur.pressure_hpa)} hPa`} />}
        {cur.apparent_temperature == null && <Metric Icon={Thermometer} label={t('weatherPage.now.temperature')} value={`${roundOrDash(cur.temperature, 1)}°C`} />}
      </div>

      <p className="text-[11px] text-ink/50 dark:text-paper/50 mt-3 leading-snug">
        {isLive || weather.status === 'STALE' ? t('weatherPage.now.modelNote') : t('weatherPage.now.demoNote')}
      </p>
    </section>
  )
}
